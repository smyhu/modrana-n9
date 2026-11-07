# -*- coding: utf-8 -*-
# HTTPS dla modRana na Nokii N9 (dodatek modrana N9, 2026).
#
# Python 2.6 na N9 ma TLS 1.0 bez SNI, a QtNetwork z latki TLS 1.2 wywraca
# proces Pythona (dwa rozne OpenSSL w jednym procesie). Dlatego HTTPS robi
# osobny maly program w C++ (tlumacz-https z cloudgps-fix), uruchomiony raz
# jako staly proces:
#   na wejscie linie "ID URL", na wyjscie "ID KOD DLUGOSC\n" + tresc
#   (KOD 0 = blad sieci, tresc = opis bledu)
# Pomocnik obsluguje wiele zapytan naraz i trzyma polaczenia otwarte.
from __future__ import with_statement
import os
import subprocess
import sys
import threading

PY3 = sys.version_info[0] >= 3

POMOCNIK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "n9", "tlumacz-https")
LATKA_TLS = "/usr/local/lib/libssl.so.1.0.0"
CZAS_MAX = 30.0


class BladPomocnika(Exception):
    pass


class _Pomocnik(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.proces = None
        self.czeka = {}
        self.licznik = 0

    def dostepny(self):
        return os.path.exists(POMOCNIK) and os.path.exists(LATKA_TLS)

    def _uruchom(self):
        # wolane z zalozonym lockiem
        self.proces = subprocess.Popen([POMOCNIK, "--serwer"], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, close_fds=True)
        watek = threading.Thread(target=self._czytaj, args=(self.proces,))
        watek.setDaemon(True)
        watek.start()
        print("pomocnik HTTPS: uruchomiony (pid %d)" % self.proces.pid)

    def _zakoncz(self, proces, powod):
        with self.lock:
            if proces is self.proces:
                self.proces = None
            czeka, self.czeka = self.czeka, {}
        try:
            proces.kill()
        except Exception:
            pass
        for wpis in czeka.values():
            wpis[1] = (0, powod)
            wpis[0].set()

    def _czytaj(self, proces):
        wyjscie = proces.stdout
        while True:
            try:
                naglowek = wyjscie.readline()
            except Exception:
                naglowek = ""
            if not naglowek:
                print("pomocnik HTTPS: zakonczyl sie")
                return self._zakoncz(proces, "pomocnik HTTPS padl")
            if PY3:
                naglowek = naglowek.decode("ascii", "replace")
            czesci = naglowek.split()
            if len(czesci) != 3:
                print("pomocnik HTTPS: zly naglowek, restart")
                return self._zakoncz(proces, "pomocnik HTTPS: zla odpowiedz")
            nr, kod, dlugosc = czesci[0], int(czesci[1]), int(czesci[2])
            tresc = wyjscie.read(dlugosc) if dlugosc else b""
            if PY3 and kod == 0:
                tresc = tresc.decode("utf-8", "replace")
            with self.lock:
                wpis = self.czeka.pop(nr, None)
            if kod == 0 and "session" in tresc:
                # po zmianie sieci (np. ponowne polaczenie Wi-Fi) staly pomocnik
                # zostaje ze stara sesja sieciowa: restart, kolejne proby pojda nowym
                print("pomocnik HTTPS: zerwana sesja sieci, restart")
                if wpis is not None:
                    wpis[1] = (kod, tresc)
                    wpis[0].set()
                return self._zakoncz(proces, "restart pomocnika")
            if wpis is not None:
                wpis[1] = (kod, tresc)
                wpis[0].set()

    def pobierz(self, adres, czas=CZAS_MAX):
        """Zwraca (kod_http, tresc). kod 0 = blad sieci (tresc = opis)."""
        if not self.dostepny():
            if not os.path.exists(LATKA_TLS):
                raise BladPomocnika("brak łatki TLS 1.2")
            raise BladPomocnika("brak pomocnika HTTPS")
        if "\n" in adres or " " in adres:
            adres = adres.replace(" ", "%20").replace("\n", "")
        wpis = [threading.Event(), None]
        with self.lock:
            if self.proces is None or self.proces.poll() is not None:
                self._uruchom()
            self.licznik += 1
            nr = str(self.licznik)
            self.czeka[nr] = wpis
            proces = self.proces
            try:
                linia = "%s %s\n" % (nr, adres)
                proces.stdin.write(linia.encode("ascii") if PY3 else linia)
                proces.stdin.flush()
            except Exception:
                self.czeka.pop(nr, None)
                self.proces = None
                raise BladPomocnika("pomocnik HTTPS nie odpowiada")
        wpis[0].wait(czas)
        if wpis[1] is None:
            with self.lock:
                self.czeka.pop(nr, None)
            return 0, "timeout"
        return wpis[1]


_pomocnik = _Pomocnik()


def pobierz(adres, czas=CZAS_MAX):
    return _pomocnik.pobierz(adres, czas)


def dostepny():
    return _pomocnik.dostepny()
