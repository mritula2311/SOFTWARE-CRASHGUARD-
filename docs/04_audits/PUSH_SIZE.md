# Repository size before pushing

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Size of the repository and of tracked files before pushing, and the options if a file in history exceeds the host limit. |
| Evidence labels used | none (this file reports no result) |
<!-- header:end -->

Measured on 2026-11-16 in the finalize run (branch `final2`). Nothing was rewritten: history, tags and branches are as they were.

| Measure | Value |
|---|---|
| Loose objects in the working repository (`git count-objects -vH`) | 5,290 objects, 376.76 MiB (nothing is packed yet) |
| Packed size of everything a push of all branches and tags would send (a bare clone with `--no-local`, which packs the objects) | 83.60 MiB in 5,229 objects |
| Branches and tags | 15 branches, 16 tags (before `submit-v3`) |
| Largest tracked file now | `results/results.json`, about 37.4 MB (limit of the host for a single file: 100 MB; a warning appears above 50 MB) |
| Tracked files over 50 MB | none |
| Blobs over 50 MB anywhere in history (`git rev-list --objects --all` with `git cat-file --batch-check`) | none |
| Blobs over 100 MB anywhere in history | none |

Release archives. Four release zips (about 35 to 37 MB each) were tracked at earlier tags (`round6-v1`, `submit-v2` and some branches). They are untracked from this commit on (`git rm --cached`, `release/*.zip` in `.gitignore`); the files stay on disk. The old tags still contain them, as intended: no history was rewritten and no tag was moved. They are already inside the 83.60 MiB above.

Result. No file in history exceeds the 100 MB limit of the host, so no rewrite is needed and no option has to be chosen. If the author later wants a smaller history, the options are (a) leave it as it is (84 MiB), (b) re-tag from commits that do not track the zips and drop the old tags, which moves tags and needs the author's approval, or (c) rewrite history with `git filter-repo` to remove `release/*.zip`, which changes every commit id from the commit that added the earliest zip and also needs the author's approval. Neither (b) nor (c) was done.
