#!/bin/bash
# Round 7 ProVerif runs (foreground, WSL): scripts/r7_formal.sh  (run from the repo root in Git Bash with MSYS_NO_PATHCONV=1 wsl -u root bash /mnt/d/.../scripts/r7_formal.sh)
R=/mnt/d/crashguard-software/crashguard-software
mkdir -p $R/formal/out/r7
for m in r7_unlink r7_unlink_many r7_unlink_control r7_unlink_bootclear r7_lemmas_alert r7_lemmas_alert_nowrite r7_lemmas_micro r7_lemmas_micro_control r7_lemmas_quarantine r7_lemmas_quarantine_control; do
  bash $R/scripts/wsl_proverif.sh $R/formal/proverif/$m.pv $R/formal/out/r7/pv_$m.txt 600
  echo "== $m: $(grep -E '^RESULT' $R/formal/out/r7/pv_$m.txt | cut -c1-200 | tr '\n' ';') $(grep -E 'wall time' $R/formal/out/r7/pv_$m.txt)"
done
