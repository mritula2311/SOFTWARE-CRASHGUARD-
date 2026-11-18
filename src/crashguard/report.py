"""Build report/software_results.md (a paper-style draft) and docs/05_data_code/FIGURES_TABLES.md from results/results.json.

Every number comes from results.json through the helpers below. They wrap each number in marker characters so a test can check that no number was typed by hand
(design constants are whitelisted in tests/test_report.py). Tables and figures are numbered in document order; text refers to them by key, so the numbers follow the
order automatically (the document is built twice: the first pass collects the numbers).
"""
from __future__ import annotations

import json
from pathlib import Path

from crashguard import config as C

L, R_ = "⟦", "⟧"  # markers around numbers taken from results.json
OUT = Path("report/software_results.md")
INDEX_OUT = Path("docs/05_data_code/FIGURES_TABLES.md")
MODEL_ORDER = ("rf15", "rf200", "lr", "gbt", "rule")
MODEL_NAMES = {"rf15": "RF, 15 trees, depth 6 (deployable)", "rf200": "RF, 200 trees", "lr": "Logistic regression",
               "gbt": "Gradient-boosted trees", "rule": "Rule (peak and duration)"}
P = f"trig_{C.TRIGGER_G:g}"
MISSING: list[tuple[str, str]] = []  # (name, "absent" | "NOT_RUN") of every result the report asked for and could not print; read by check_results.py


class Res:
    def __init__(self, path: Path = Path("results/results.json")):
        self.r = {e["name"]: e for e in json.loads(path.read_text(encoding="utf-8"))}

    def _miss(self, name: str) -> None:
        MISSING.append((name, "absent" if name not in self.r else "NOT_RUN"))

    def has(self, name: str) -> bool:
        return name in self.r

    def v(self, name: str):
        return self.r[name]["value"]

    def f(self, name: str, d: int = 3) -> str:
        if name not in self.r or self.r[name]["value"] in ("NOT_RUN", None):
            self._miss(name)
            return "NOT_RUN"
        x = self.r[name]["value"]
        return f"{L}{x:.{d}f}{R_}"

    def ci(self, name: str, d: int = 3) -> str:
        """value [lower to upper] using name, name_lo and name_hi."""
        return f"{self.f(name, d)} [{self.f(name + '_lo', d)} to {self.f(name + '_hi', d)}]"

    def _num(self, name: str):
        x = self.r.get(name, {}).get("value")
        return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None

    def i(self, name: str) -> str:
        x = self._num(name)
        if x is None:
            self._miss(name)
        return f"{L}{int(x)}{R_}" if x is not None else "NOT_RUN"

    def sci(self, name: str) -> str:
        x = self._num(name)
        if x is None:
            self._miss(name)
        return f"{L}{x:.2e}{R_}" if x is not None else "NOT_RUN"

    def ms(self, prefix: str, d: int = 3) -> str:
        return f"{self.f(prefix + '.mean', d)} ± {self.f(prefix + '.std', d)}"

    def origin(self, name: str) -> str:
        return self.r[name]["origin"] if name in self.r else "NOT_RUN"

    def text(self, name: str) -> str:
        return str(self.r[name]["value"]) if name in self.r else "NOT_RUN"


def table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


class Doc:
    """Collects the lines, numbers tables and figures in order, and keeps an index of them for docs/05_data_code/FIGURES_TABLES.md."""

    def __init__(self, nums: dict | None = None):
        self.lines: list[str] = []
        self.nums = nums or {}
        self.found: dict[str, int] = {}
        self.index: list[dict] = []
        self.fig_found: dict[str, int] = {}

    def a(self, s: str) -> None:
        self.lines.append(s)

    def tab(self, key: str, title: str, origin: str, keys: str, claim: str) -> None:
        n = len(self.found) + 1
        self.found[key] = n
        self.index.append(dict(kind="Table", n=n, key=key, title=title, origin=origin, keys=keys, claim=claim))
        self.a(f"### Table {n}. {title} ({origin})\n")

    def T(self, key: str) -> str:
        return f"Table {self.nums.get(key, '?')}"

    def fig(self, name: str, caption: str, origin: str, keys: str, claim: str) -> None:
        if not (C.FIGURES / f"{name}.png").exists():
            return
        n = len(self.fig_found) + 1
        self.fig_found[name] = n
        self.index.append(dict(kind="Figure", n=n, key=name, title=caption, origin=origin, keys=keys, claim=claim))
        self.a(f"**Figure {n}.** {caption} ({origin})  \n![{name}](../results/figures/{name}.png)\n")

    def F(self, name: str) -> str:
        return f"Figure {self.nums.get('fig:' + name, '?')}"


def _compose(r: Res, d: Doc) -> None:
    from crashguard import report_part1 as P1
    from crashguard import report_part2 as P2
    from crashguard import report_part3 as P3
    from crashguard import report_part4 as P4
    from crashguard import report_part5 as P5
    from crashguard import report_part6 as P6
    from crashguard import report_part7 as P7
    from crashguard import report_part8 as P8

    d.a("# CrashGuard: software results (paper-style draft)\n")
    d.a("Generated by `make report` from `results/results.json`. Every number below comes from code run in this repository. "
        "Each table and figure names its origin: MEASURED_SOFTWARE (computed from a dataset), SIMULATED (a simulation with stated assumptions), ANALYTICAL (a formula or a datasheet value), "
        "HARDWARE (the author's logs) or NOT_RUN. Tables and Figures are numbered in order of appearance and indexed in `docs/05_data_code/FIGURES_TABLES.md`. This is a software-only draft: nothing here is a measurement on the car, the ESP32 or the radios.\n")
    P1.introduction(r, d)
    P1.dataset(r, d)
    P1.method(r, d)
    d.a("## 4. Results\n")
    P1.detector(r, d)
    P4.prevalence_section(r, d)
    P1.trigger_section(r, d)
    P1.robustness(r, d)
    P1.size_section(r, d)
    P2.severity_section(r, d)
    P2.security_section(r, d)
    P2.replay_section(r, d)
    P3.algorithms_section(r, d)
    P3.lora_and_hardware(r, d)
    P5.extra_intro(r, d)
    P5.x1_section(r, d)
    P5.x2_section(r, d)
    P5.x3_section(r, d)
    P5.x4_section(r, d)
    P6.x5_section(r, d)
    P6.x6_section(r, d)
    P6.x7_section(r, d)
    P7.round3_section(r, d)
    P8.closing_section(r, d)
    P3.figures_note(r, d)
    P3.limitations(r, d)
    P3.threats(r, d)
    P3.hardware_needed(r, d)
    P3.reproduce(r, d)


def build(res: Res | None = None) -> str:
    r = res or Res()
    first = Doc()
    _compose(r, first)
    nums = dict(first.found)
    nums.update({"fig:" + k: v for k, v in first.fig_found.items()})
    second = Doc(nums)
    _compose(r, second)
    build.last_doc = second  # type: ignore[attr-defined]
    return "\n".join(second.lines)


def write_index(d: Doc) -> None:
    rows = ["# Figures and tables: index", "",
            "Generated by `make report` (`src/crashguard/report.py`) next to `report/software_results.md`. For each figure and table: the origin label, the `results/results.json` key prefixes "
            "behind it, and the claim it supports. Origin labels: MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, HARDWARE, NOT_RUN.", "",
            "| Item | Title | Origin | results.json keys | Claim it supports |", "|---|---|---|---|---|"]
    for e in d.index:
        rows.append(f"| {e['kind']} {e['n']} | {e['title']} | {e['origin']} | {e['keys']} | {e['claim']} |")
    INDEX_OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    text = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text.replace(L, "").replace(R_, ""), encoding="utf-8")
    write_index(build.last_doc)  # type: ignore[attr-defined]
    print(f"wrote {OUT} ({len(text)} characters) and {INDEX_OUT}")


if __name__ == "__main__":
    main()
