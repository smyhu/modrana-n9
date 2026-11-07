# modRana for Nokia N9 (modrana-n9)

modRana 0.43.4 brought back to life on the Nokia N9 (MeeGo Harmattan PR1.3) in 2026.

modRana is a flexible GPS navigation program by **Martin Kolman**
([github.com/M4rtinK/modrana](https://github.com/M4rtinK/modrana), GPL-3).
Its last Harmattan build (0.43.4, 2013) still installs, but almost all of its
map servers are gone and today's servers need HTTPS with TLS 1.2, which the
N9 cannot do on its own. This repository keeps the N9 build working.

## What is changed (0.43.4-n9.x)

- **Maps:** a new 2026 list of working map layers and overlays
  (OpenStreetMap, OpenTopoMap, CyclOSM, Esri, Google, Bing, Waymarked Trails
  hiking/cycling/MTB/ski/riding/skating, OpenRailwayMap, OpenSeaMap, hillshading, ...).
- **HTTPS:** map tiles and address search (Nominatim) over HTTPS through a small
  native helper (`src/n9/https-helper`, source in `helper/`), because Python 2.6
  on the N9 cannot do modern TLS and must not load the patched QtNetwork itself.
- **Messages:** on-screen error messages for map and search failures
  (`CronQt.addIdle` was empty in 0.43.4, so messages were never shown).
- **Overlays:** press and hold an overlay to select it; *remove* deletes only the selected one.
- **Icon** in the style of the N9 home screen.
- n9.4: recognises both TLS 1.2 patches for the N9 (see below); English names and messages.

The full history is in the commits: the first commit is the unmodified
upstream 0.43.4 Harmattan tree, the following ones are the N9 changes.

## Requirements

- Nokia N9 with Harmattan PR1.3
- a TLS 1.2 patch for the N9 for HTTPS maps and search:
  [n9-tls](https://github.com/smyhu/n9-tls) (recommended) or the older WunderWungiel patch.
  Without it only the plain-HTTP maps work.
- `aegis-dpkg` (from the Aegis installer hack in N9QTweak) to install packages.

## Install

Copy `dist/modrana_0.43.4-n9.4_armel.deb` to the phone, then as root:

```
aegis-dpkg -i /home/developer/modrana_0.43.4-n9.4_armel.deb
```

If modRana was installed from the Ovi Store / OpenRepos, Aegis refuses to replace it
("less trusted source"): remove it first with `aegis-dpkg -r modrana`
(your settings in `~/.modrana` and the map cache in `MyDocs/.maps` stay).
The [MeeRevive](https://github.com/smyhu/meerevive-n9) installer does this automatically.

## Build

```
sh packaging/build-deb.sh
```

builds `dist/modrana_<version>_armel.deb` from `src/` on any Linux with `dpkg-deb`,
`ar` and `python3`. The helper is cross-built with `helper/build.sh` (needs an ARM
hard-float cross compiler and unpacked Harmattan packages as sysroot).

## Licence and credits

- modRana: © Martin Kolman and contributors, **GPL-3** (see `LICENSE`).
- N9 changes in this repository: GPL-3 as well.
- `helper/` (https-helper): MIT.

Designed and written by Claude (Anthropic) together with smyhu for Nokia N9.
