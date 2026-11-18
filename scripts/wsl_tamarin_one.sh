#!/bin/bash
# usage: wsl_tamarin_one.sh <outfile-in-WSL> <tamarin args...>
export PATH=/usr/local/bin:/usr/bin:/bin
export MAUDE_LIB=/opt/maude
out="$1"; shift
cd /tmp
/opt/tamarin/tamarin-prover "$@" > "$out" 2>&1
echo "exit $?" >> "$out"
