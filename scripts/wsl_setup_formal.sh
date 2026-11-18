#!/bin/bash
# Installs the formal-verification tools used by T2 (run once, as root, inside WSL Ubuntu 24.04).
# Tamarin 1.12.0 needs Maude 3.2.1 or newer; the Ubuntu package is 3.2, so Maude 3.5.1 is taken from its release page.
set -e
export PATH=/usr/local/bin:/usr/bin:/bin
mkdir -p /opt/maude /opt/tamarin
cd /opt/maude
[ -f m.zip ] || curl -sL -m 300 -o m.zip https://github.com/maude-lang/Maude/releases/download/Maude3.5.1/Maude-3.5.1-linux-x86_64.zip
apt-get install -y unzip >/dev/null 2>&1 || true
unzip -qo m.zip
ls /opt/maude
