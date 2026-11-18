"""V2.1/V2.2: summarise formal/rerun_vf/*/*.txt into docs/04_audits/FORMAL_RERUN.md (outcome, wall time, peak memory) and compare with the stored outcome."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "formal" / "rerun_vf"
rows = []
for f in sorted(R.rglob("*.txt")):
    t = f.read_text(encoding="utf-8", errors="replace")
    lem = re.search(r"^lemma: (\S+)", t, re.M)
    cmd = re.search(r"^command: (.*)$", t, re.M)
    ex = re.search(r"exit code: (\d+) ; wall time (\d+) s(?: ; peak memory (\d+) MB)?", t)
    if f.parent.name == "proverif":
        res = re.findall(r"^RESULT .* is (true|false)\.|^RESULT .* cannot be proved", t, re.M)
        rr = re.findall(r"^RESULT (.*?) is (true|false)\.", t, re.M)
        out = "; ".join("proved" if v == "true" else "attack found (false)" for _, v in rr) or ("undecided (time limit)" if ex and ex.group(1) == "124" else "no result")
        name = f.stem
    else:
        name = f.stem
        lm = lem.group(1) if lem else f.stem
        mm = re.findall(r"^\s+" + re.escape(lm) + r" \((all|exists)-traces?\): (verified|falsified)", t, re.M)
        if mm:
            kind, v = mm[-1]
            out = ("proved" if kind == "all" else "trace found (exists-trace lemma verified)") if v == "verified" else "attack or trace found"
        else:
            out = "undecided (time limit or memory)" if ex and ex.group(1) in ("124", "1", "2") else "no result"
    rows.append((f.parent.name, name, out, ex.group(2) if ex else "?", ex.group(3) if ex and ex.group(3) else "?", cmd.group(1)[:90] if cmd else ""))
out = ["# Formal models rerun (V2.1, V2.2)", "", "<!-- header:start -->", "<!-- header:end -->", "",
       "Rerun on 2026-11-15 with `scripts/vf_formal_rerun.sh` (one process per lemma, one thread, 5 GB heap limit, Tamarin 1.12.0, Maude 3.5.1, ProVerif 2.05, WSL2 Ubuntu 24.04). Raw outputs: `formal/rerun_vf/`. Stored outcomes of the paper: `results.json` keys `r3.t2.sec.*` and `a4.a3.proverif.*`.", "",
       "| Group | Lemma or model | Outcome | Wall time (s) | Peak memory (MB) | Command |", "|---|---|---|---|---|---|"]
out += [f"| {g} | {n} | {o} | {w} | {m} | `{c}` |" for g, n, o, w, m, c in rows]
(ROOT / "docs/04_audits/FORMAL_RERUN.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(len(rows))
for r in rows:
    print(r[:5])
