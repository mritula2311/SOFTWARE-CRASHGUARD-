# First message to paste into Claude Code

<!-- header:start -->
| Field | Value |
|---|---|
| Status | archived (superseded) |
| Date | 2026-11-10 |
| Owner | Mritula S |
| Scope | Opening message of the initial session. |
| Evidence labels used | NOT_RUN |
| Replaced by | `CLAUDE.md and docs/00_overview/PRD.md` |
| Reason | it holds no instruction that the PRD lacks |
<!-- header:end -->

Read CLAUDE.md and every file in docs/ first. Then build the project milestone by milestone as in docs/00_overview/PRD.md §9 (M1 → M6). After each milestone:
- run the tests;
- update the README Status table;
- commit.

Start with M1 (`make data`). If the dataset cannot be downloaded or differs from docs/05_data_code/DATASET.md, stop and tell me before continuing. Never invent a result; use NOT_RUN where something cannot be run.
