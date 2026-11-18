#!/usr/bin/env bash
# Compile and run every C equivalence check with gcc and write one JSON file that `python -m crashguard.merge_c_checks` can import into results/results.json.
#
#   scripts/c_checks.sh [OUT.json]        default OUT = build/c_checks.json
#   CC=clang scripts/c_checks.sh          choose another C compiler (default gcc)
#
# Bundles: c_bundle/ (committed; synthetic inputs) and build/c_bundle_real/ (git-ignored; the real test events and windows, built by `python -m crashguard.c_bundle --real`).
# Needs only bash, python3 (standard library) and a C compiler. Run it on Linux, under WSL (`wsl bash scripts/c_checks.sh`) or on a CI runner (.github/workflows/c_checks.yml).
# Exit code 0 if every check ran and passed, 1 otherwise. A check that cannot be compiled or run is written with "ran": false and the reason; nothing is invented.
set -u
cd "$(dirname "$0")/.."
OUT="${1:-build/c_checks.json}"
CC="${CC:-gcc}"
RUN=build/c_run
mkdir -p "$RUN" "$(dirname "$OUT")"
FRAGS="$RUN/fragments.jsonl"
: > "$FRAGS"
status=0

cc_version="$($CC --version 2>&1 | head -1)"
for bundle in c_bundle build/c_bundle_real; do
  [ -f "$bundle/manifest.json" ] || continue
  tag="$(basename "$bundle")"
  names="$(python3 -c "import json,sys; print(' '.join(c['name'] for c in json.load(open('$bundle/manifest.json'))['checks']))")"
  for name in $names; do
    dir="$bundle/$name"
    exe="$RUN/${tag}_${name}"
    out="$RUN/${tag}_${name}.out"
    rm -f "$exe" "$out"
    if ! $CC -O2 -std=c99 -I"$dir" "$dir/harness.c" -o "$exe" -lm 2> "$RUN/${tag}_${name}.cc.log"; then
      reason="$(head -c 300 "$RUN/${tag}_${name}.cc.log" | tr '\n"' '  ')"
      echo "{\"bundle\":\"$tag\",\"name\":\"$name\",\"ran\":false,\"passes\":false,\"reason\":\"compile failed: $reason\"}" >> "$FRAGS"
      status=1
      continue
    fi
    if ! "$exe" "$dir/in.bin" "$out" 2> "$RUN/${tag}_${name}.run.log"; then
      echo "{\"bundle\":\"$tag\",\"name\":\"$name\",\"ran\":false,\"passes\":false,\"reason\":\"program returned an error\"}" >> "$FRAGS"
      status=1
      continue
    fi
    frag="$(python3 scripts/c_compare.py "$bundle" "$name" "$out")" || status=1
    python3 - "$tag" "$frag" >> "$FRAGS" <<'PY'
import json, sys
d = json.loads(sys.argv[2]); d["bundle"] = sys.argv[1]; d["ran"] = True
print(json.dumps(d))
PY
  done
done

python3 - "$OUT" "$CC" "$cc_version" "$FRAGS" <<'PY'
import json, platform, sys
out, cc, ver, frags = sys.argv[1:5]
checks = [json.loads(l) for l in open(frags) if l.strip()]
doc = dict(platform=platform.platform(), system=platform.system(), machine=platform.machine(), compiler=cc, compiler_version=ver, python=platform.python_version(),
           all_ran=all(c.get("ran") for c in checks) and bool(checks), all_passed=all(c.get("passes") for c in checks) and bool(checks), checks=checks)
json.dump(doc, open(out, "w"), indent=1)
print(f"wrote {out}: {len(checks)} checks, all ran: {doc['all_ran']}, all passed: {doc['all_passed']}")
for c in checks:
    worst = max((f.get("max_abs_diff", 0.0) for f in c.get("fields", {}).values()), default=float("nan"))
    print(f"  {c['bundle']}/{c['name']}: ran={c.get('ran')} passes={c.get('passes')} max_abs_diff={worst:.3g} {c.get('reason', '')}")
PY
exit $status
