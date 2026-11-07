# -*- coding: utf-8 -*-
# HTTPS for modRana on the Nokia N9 (modRana N9 addition, 2026).
#
# Python 2.6 on the N9 only speaks TLS 1.0 without SNI, and the TLS 1.2
# patched QtNetwork crashes a Python process (two different OpenSSL versions
# in one process). So HTTPS is done by a small separate C++ program
# (n9/https-helper, source in helper/ of the modrana-n9 repository), started
# once as a long-running process:
#   input lines "ID URL", output "ID CODE LENGTH\n" + body
#   (CODE 0 = network error, body = error description)
# The helper serves many requests at once and keeps connections open.
from __future__ import with_statement
import os
import subprocess
import sys
import threading

PY3 = sys.version_info[0] >= 3

HELPER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "n9", "https-helper")
# TLS 1.2 patch for the N9: n9-tls (github.com/smyhu/n9-tls) or the older
# WunderWungiel patch - either one makes QtNetwork speak TLS 1.2
TLS_PATCH_FILES = ("/usr/lib/libssl.so.1.0.2", "/usr/local/lib/libssl.so.1.0.0")
MAX_WAIT = 30.0


def tls_patch_installed():
    for f in TLS_PATCH_FILES:
        if os.path.exists(f):
            return True
    return False


class HelperError(Exception):
    pass


class _Helper(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None
        self.waiting = {}
        self.counter = 0

    def available(self):
        return os.path.exists(HELPER) and tls_patch_installed()

    def _start(self):
        # called with the lock held
        self.process = subprocess.Popen([HELPER, "--serwer"], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, close_fds=True)
        reader = threading.Thread(target=self._read, args=(self.process,))
        reader.setDaemon(True)
        reader.start()
        print("HTTPS helper: started (pid %d)" % self.process.pid)

    def _stop(self, process, reason):
        with self.lock:
            if process is self.process:
                self.process = None
            waiting, self.waiting = self.waiting, {}
        try:
            process.kill()
        except Exception:
            pass
        for entry in waiting.values():
            entry[1] = (0, reason)
            entry[0].set()

    def _read(self, process):
        out = process.stdout
        while True:
            try:
                header = out.readline()
            except Exception:
                header = ""
            if not header:
                print("HTTPS helper: exited")
                return self._stop(process, "HTTPS helper crashed")
            if PY3:
                header = header.decode("ascii", "replace")
            parts = header.split()
            if len(parts) != 3:
                print("HTTPS helper: bad header, restarting")
                return self._stop(process, "HTTPS helper: bad reply")
            nr, code, length = parts[0], int(parts[1]), int(parts[2])
            body = out.read(length) if length else b""
            if PY3 and code == 0:
                body = body.decode("utf-8", "replace")
            with self.lock:
                entry = self.waiting.pop(nr, None)
            if code == 0 and "session" in body:
                # after a network change (e.g. Wi-Fi reconnect) the long-running
                # helper keeps the old network session: restart it, next tries use a new one
                print("HTTPS helper: network session lost, restarting")
                if entry is not None:
                    entry[1] = (code, body)
                    entry[0].set()
                return self._stop(process, "HTTPS helper restarted")
            if entry is not None:
                entry[1] = (code, body)
                entry[0].set()

    def fetch(self, url, timeout=MAX_WAIT):
        """Returns (http_code, body). Code 0 = network error (body = description)."""
        if not self.available():
            if not tls_patch_installed():
                raise HelperError("TLS 1.2 patch is not installed")
            raise HelperError("HTTPS helper is missing")
        if "\n" in url or " " in url:
            url = url.replace(" ", "%20").replace("\n", "")
        entry = [threading.Event(), None]
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self._start()
            self.counter += 1
            nr = str(self.counter)
            self.waiting[nr] = entry
            process = self.process
            try:
                line = "%s %s\n" % (nr, url)
                process.stdin.write(line.encode("ascii") if PY3 else line)
                process.stdin.flush()
            except Exception:
                self.waiting.pop(nr, None)
                self.process = None
                raise HelperError("HTTPS helper does not respond")
        entry[0].wait(timeout)
        if entry[1] is None:
            with self.lock:
                self.waiting.pop(nr, None)
            return 0, "timeout"
        return entry[1]


_helper = _Helper()


def fetch(url, timeout=MAX_WAIT):
    return _helper.fetch(url, timeout)


def available():
    return _helper.available()
