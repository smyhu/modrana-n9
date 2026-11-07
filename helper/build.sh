#!/bin/sh
# Cross-builds https-helper for the N9 (Harmattan, armv7 hard-float).
# Usage: SYSROOT=<unpacked Harmattan packages> sh build.sh https-helper.cpp https-helper
set -e
C=arm-linux-gnueabihf; R=${SYSROOT:?set SYSROOT to unpacked Harmattan packages}
GI=$($C-gcc -print-file-name=include)
F="-nostdinc -isystem /usr/$C/include/c++/13 -isystem /usr/$C/include/c++/13/$C -isystem $R/usr/include -isystem $GI -idirafter /usr/$C/include -I$R/usr/include/qt4 -DQT_NO_STL -U_TIME_BITS -U_FILE_OFFSET_BITS -std=gnu++98 -O2 -march=armv7-a -mfpu=vfpv3-d16 -mfloat-abi=hard -mthumb -fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-stack-protector -U_FORTIFY_SOURCE"
$C-g++ $F -c "$1" -o t.o
$C-g++ $F -c new.cpp -o n.o
$C-g++ -no-pie -march=armv7-a -mfloat-abi=hard -nodefaultlibs -nostartfiles $R/usr/lib/crt1.o $R/usr/lib/crti.o $($C-gcc -print-file-name=crtbegin.o) t.o n.o -L$R/usr/lib -L$R/lib -Wl,--allow-shlib-undefined -Wl,--hash-style=both -Wl,-z,norelro -Wl,--dynamic-linker=/lib/ld-linux.so.3 -lQtNetwork -lQtCore $R/usr/lib/libc_nonshared.a $R/lib/libc.so.6 $($C-gcc -print-libgcc-file-name) $($C-gcc -print-file-name=crtend.o) $R/usr/lib/crtn.o -o "$2"
$C-strip "$2"
