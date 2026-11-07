#!/bin/sh
# Builds modrana_<version>_armel.deb for Nokia N9 (Harmattan) from src/.
# Needs: dpkg-deb, ar, python3, sha1sum, md5sum (any Linux).
# Usage: sh packaging/build-deb.sh [output-dir]
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
VERSION=$(sed -n 's/^V\([^ ]*\).*/\1/p' "$ROOT/src/version.txt")
OUT=${1:-$ROOT/dist}
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/data/opt/modrana" "$T/data/usr/share/applications" \
         "$T/data/usr/share/icons/hicolor/80x80/apps" "$T/data/usr/share/icons/hicolor/64x64/apps" "$T/ctl" "$OUT"
cp -r "$ROOT/src/." "$T/data/opt/modrana/"
cp "$ROOT/packaging/debian/modrana.desktop" "$T/data/usr/share/applications/"
cp "$ROOT/icons/modrana80.png" "$T/data/usr/share/icons/hicolor/80x80/apps/modrana.png"
cp "$ROOT/icons/modrana64.png" "$T/data/usr/share/icons/hicolor/64x64/apps/modrana.png"
find "$T/data/opt/modrana" -name '*.pyc' -delete
find "$T/data/opt/modrana" -type d -name __pycache__ -exec rm -rf {} +
chmod -R u+rwX,go+rX,go-w "$T/data"
chmod 755 "$T/data/opt/modrana/n9/https-helper" "$T/data/opt/modrana/modrana.py" "$T/data/opt/modrana/run"
cp "$ROOT/packaging/debian/postinst" "$ROOT/packaging/debian/_aegis" "$T/ctl/"
SIZE=$(du -sk "$T/data" | cut -f1)
python3 - "$ROOT/packaging/debian/control" "$T/ctl/control" "$VERSION" "$SIZE" "$ROOT/icons/modrana64.png" <<'P'
import sys, base64
src, dst, version, size, icon = sys.argv[1:]
b = base64.b64encode(open(icon, "rb").read()).decode("ascii")
lines = "\n".join(" " + b[i:i + 76] for i in range(0, len(b), 76))
t = open(src).read().replace("@VERSION@", version).replace("@SIZE@", size).replace("@ICON@", lines)
open(dst, "w").write(t)
P
(cd "$T/data" && find . -type f | sed 's#^\./##' | sort | xargs md5sum) > "$T/ctl/md5sums"
# digsigsums in the format of Nokia packages (all files + maintainer script)
entry() { printf 'S 15 com.nokia.maemo H 40 %s R %d %s\n' "$1" "${#2}" "$2"; }
(
    cd "$T/data"
    find . -type f | sed 's#^\./##' | sort | while read -r f; do
        entry "$(sha1sum "$f" | cut -d' ' -f1)" "$f"
    done
    entry "$(sha1sum "$T/ctl/postinst" | cut -d' ' -f1)" "var/lib/dpkg/info/modrana.postinst"
) > "$T/ctl/digsigsums"
chmod 644 "$T/ctl/control" "$T/ctl/md5sums" "$T/ctl/digsigsums" "$T/ctl/_aegis"; chmod 755 "$T/ctl/postinst"
(cd "$T/ctl" && tar czf ../control.tar.gz --owner=0 --group=0 --numeric-owner --format=gnu ./control ./md5sums ./digsigsums ./postinst)
(cd "$T/data" && tar czf ../data.tar.gz --owner=0 --group=0 --numeric-owner --format=gnu .)
echo 2.0 > "$T/debian-binary"
cp "$T/ctl/_aegis" "$T/_aegis"
DEB="$OUT/modrana_${VERSION}_armel.deb"
rm -f "$DEB"
(cd "$T" && ar rc "$DEB" debian-binary control.tar.gz data.tar.gz _aegis)
md5sum "$DEB"
