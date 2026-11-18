# Sealed split of the pooled NHTSA records (Z0)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-12 |
| Owner | Mritula S |
| Scope | The sealed split of pooled NHTSA records and its access rules. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | NHTSA = National Highway Traffic Safety Administration |
<!-- header:end -->

Written before any model of the positive-results push was fitted (see `docs/02_preregistration/PREREGISTRATION_V4.md`). **The SEALED fold is scored once per hypothesis**, after the model and its settings are frozen in a commit; every scoring is logged in `results/tables/p_sealed_access.csv` (hypothesis, time, freeze commit).

## What is pooled

- The 176 rows of the N13/N14 set, minus the two duplicated rows of tests 3668 and 3904 (same channel loaded twice under a wrong vehicle label; the signals were checked to be identical) = 174 records.
- The 739 held-out records of T13a (`t13.heldout.*`; selection rules in `docs/07_log/DECISIONS.md`).
- **913 records in 325 make-and-model groups.** Reference delta-V is the N13 reference; classes use the limits 24, 40 and 56 km/h (Low, Moderate, Severe, Critical).

Modes: frontal barrier = the original frontal tests (barrier at 0 degrees); side = the original left-side tests (impactor at 270 degrees); pole = vehicle into pole at any angle; other = every other configuration of T13a (oblique barrier, vehicle into vehicle, impactor at another angle). The mode is the crash configuration of the test record; a deployed node does not know it (Z1).

Group key = make and the leading word of the model name (upper case), a conservative merge of variants of one vehicle (for example COROLLA and COROLLA HYBRID go to one group). Split: groups are shuffled with seed 42 inside the stratum of their primary mode and cut at 60% and 80% of the stratum's records; all records of a group are in one fold.

## Records by fold and mode

| fold | frontal barrier | pole | side | other | all |
|---|---|---|---|---|---|
| development | 68 | 311 | 36 | 128 | 543 |
| validation | 28 | 103 | 8 | 45 | 184 |
| SEALED test | 20 | 115 | 14 | 37 | 186 |
| all | 116 | 529 | 58 | 210 | 913 |

## Records by fold and class

| fold | Low | Moderate | Severe | Critical |
|---|---|---|---|---|
| development | 21 | 291 | 149 | 82 |
| validation | 5 | 98 | 47 | 34 |
| SEALED test | 7 | 117 | 33 | 29 |

## Groups by fold

- **development**: 189 groups, 543 records. Digest of the sorted group keys (SHA-256 of the keys joined by newlines): `c3d527f74ad4b59638381a5004cdb79efa2570e38d5e0ba537e96179186bda5e`
- **validation**: 65 groups, 184 records. Digest of the sorted group keys (SHA-256 of the keys joined by newlines): `df9ec2e8edaada36ebd42665ccb2725d005a27fa862c090d1cc05b89428382a0`
- **SEALED test**: 71 groups, 186 records. Digest of the sorted group keys (SHA-256 of the keys joined by newlines): `ab69ec7a1a7d5d4ce618663227b54690c0c2b570101dbac0b236a1b84fc73365`

To check a fold, rebuild the group keys with `crashguard.pp_pool.group_key` and compare the digest and the per-group hashes below (SHA-256 of the key, leading 12 hex characters).

### development group hashes (189)

0076ed74b34c 016a63ff5559 04a05cbc7ef3 07d454c1bde3 0953ef94ad8d 09710e358e21 0abcd0486c9c 0ae24ab2ca15 0b44775b4662 0be2f11506f5 0ee753f8c64a 0fa07d9bf870 115a40dd4a3d 13117a9b2fd0 160647122b80 1674d0a46a3c 1702f8bbbe3d 19ae1d75b8e2 1a5e9ee3efa1 1aad08c75669 1cd4632bf682 1d8074674b75 1d9058680ffa 1e9e75458e73 1f3a0cd9c0f1 210dc4093928 26a9a8022436 277b63f2cb16 288627add6dd 29ac58725eb4 2ac84404d659 2c871f57dccb 2f5cacac094c 2f9db25d178a 3107dd759d1e 31544674da47 3425881cf56c 34b7b1a85617 36dc704eebed 37fd63814f25 3a952283c3fc 3ebae1564f6d 3ffcee52a45b 4378a5b1c87c 46867cdaa858 4b58ccc3ba5a 4bdfc2cbfcd1 4bea9252479e 4c1837efe719 4ca10eaefed8 4cc27ad928f9 4d0764a6c658 50264e687b05 5106e051f819 5181ceba7da7 53e7a398df14 54020037f2f5 5446fbf5ff8b 549eef252eac 553f82c15919 55459fb6a55e 57e55866af2d 5845088421bc 5900c7ad27d1 5914652fdab9 596571817e9d 5b334a97dfe5 5cb9871ac151 5cd19d2bb0c9 5f4a4e6cb046 60903d7a2d6b 61c8d036fca0 61f6157f7f31 62944055a7e4 632a97a5a466 632fab88a14c 635bbc1a6fdc 64ff23f91414 66c7fb4b88a6 67ccda909486 68a15b878582 68f97f4342fc 6930509d2007 695f5a682744 6ab3ef9bed4d 6bd64d5b01f8 6bdac3e5c400 6beaa531f2a7 6f8dfa60f85a 70304b045c30 7069b937443f 7168585e87cf 73795b5ecdb9 759e43f6209b 75f9f5fdeaa0 76cfd7a122c1 776e087c0c83 78f6f0f80b3f 794ecf146a1e 7a2173c63fb5 7b12e02b3c44 7bd87f097cae 7cc1b2ac304e 7d606b87a2e2 7f64a1c8f1ea 802c3f81289b 80f48be6e7b2 8167b49fc2e5 842921d74e44 86f90d61ee85 8895f26fbe2d 89c3433e036d 89c96d222d65 8ab955d3cb22 8c86a4880822 8ce1f13eb756 9407f05328dc 952ce0f838a1 954a170bba32 9783e6ce80d1 97d21ad387cc 9842f51c58b2 995aa4c8803e 9b035524992c 9da68cfe89e6 9ee0a1e41528 a0ae19130910 a13f1e4f3cff a5a4db81be42 abf753875b03 aeb5a23839aa b0e7883f255b b14d8973ef5f b153eeefa310 b58fb1d446a6 b62847b4f67a b6cb2a7ed08f bbda13ddf730 bc1871d74f8a bc710b7f0d8c be800d8bd8a3 beb978ad3658 bfc8e8faa0e4 c02282318cb2 c15d0a0afb35 c1b0d6dc4de1 c5006b73485d c6addf9e6748 c897a065c78e caa1da02924e cb853b7a296c cb8c26a43db2 cc59f701561a cd38f8fe90e5 cf1c1978ce2c d03a1bb86922 d2f15bcf2be7 d367e89f77a7 d368e9c53698 d40c0ce3f0fe d51ef2ecc3e5 d92f98c8b4ae da44608f1fd9 daf335e4de31 db9772fcd64e dc409e8387e2 df9b7a11585a e0cb8de697b8 e14cd7825ad6 e290256086dc e30554ca42b2 e4c946427522 e5a87b8074b8 e84eb57d371a e9ab58e15a37 eacfba63b39c eb1886d5b11a eb50495eeb14 ec5a5ee4eb41 ee5bef703995 ef6a035f11a6 f13f2a8c8378 f3be1884f3fa f4ff3d59dca8 f67d9ad0167b f933e2dc1c5d f94749e7a817 fd610ebee5cb fe6e97b302ff

### validation group hashes (65)

02a4bf6d1e0d 052e7c481744 0ad0a684ee29 129d84bc046b 13ca9ccedc4e 1cebe2b072b9 20a0adde45ba 219c0e2d7bd0 244e00ccd1f8 26b2c414b014 2b7a652c5626 2de1a91a6071 2df325070104 31873929c53e 321e67f7694c 32592440912f 40ea2738e3f5 427d0ed629a3 4bfe9fdc1bab 4ef7bf29b09b 5337b03e7bc9 552f5a26f13e 57ded7928128 5890f713fd78 5cfb3888827c 5d4d4c1241d5 62ed4ed35cd0 676ce935c93c 6a435b0462ff 6e074d625e4d 729f6543485e 76767b682858 78010238e65b 7d9dedbd2b7e 87a7ebc2d43d 8c7c0f395fce 8d9f6329b460 91c95394ad1d 97dd6c0c5d6f a5ba32df84d9 a92bffae6fbf a9c7aea0f945 ac8e67ad1a0d ace04670dbef b2b37f12062e b527e023547d bb621a062f93 c06f38e8c379 c3c4ee8a9f1e c9033beb955e cac4906c8369 cd966b50c730 d134741894e7 d2edb1d6ed76 d409eb7daf5e d5f350b99b0e de4a2b4bd183 e14c7e9d99aa e2cac0dcb550 e4773ff910a3 e5c178cd3c38 e9cab0821197 f290b1f2ae1e f4602a1902cd f8facc0ab33e

### SEALED test group hashes (71)

007e3b92c2d8 0694b1161f50 07502bf7c0f4 0880dbd8c331 0f5e3709f0ac 120ab12e297f 13d627b62592 13ff7a0d56f0 16f4d2e0d366 1f7ee60c1788 23dd6ec29b3c 2db890415eb6 31065ffa3661 3867e9bd4fa1 3b9770f58e58 430cc3666098 434f6d2ac418 469bce2e7c2b 46b5958ba86f 4a45b99d1d87 514fff682b4e 5cc5cf24a096 5eddeadd4b7f 6037bc9c3f9d 6103ad1cd5d0 65f43abd0bdc 6a33e9f44f05 6ab7e8554f2f 709fd3d68019 76c772528a62 7ba2ccf4e001 7d505f05f253 7e5d075bbe17 7ef9aa785a82 843a72d8b37a 84c3815a3b9e 865aa1c2331d 8e1d776a0162 9514ad24f37b 95631b9ba2fa 96111dcadc9e 9aaa78c39a2d a1a5c9ebecd1 a6230b077a66 a73e6213898c b2be684ef411 b996fd0087a3 bbbe5fc631e1 bd3e1677ae50 bdc8760b8c4c be5d3a675241 bea1eb8a1662 c11b83b52646 c141311d4740 c35ccae47f08 c5f6c25f2e3e ca53268ee273 ca8284ba95d1 ce2cc3edfa8d cec52f5b4ebb cfa76ff7588d de01970e0db2 e2e1a1173026 e4475705a6fd e5b487671baf e6b9d9baffdf eba4024b0e4f ec1fbd7f6f9b f03fa13b9b8d f2b6eaf46891 f56604d101cd

## Sealed-fold scorings

Generated from `results/tables/p_sealed_access.csv` (rows are written by `pp_common.sealed_gate`; a repeat needs a stated deviation). Each freeze commit holds `results/tables/p_freeze_<hypothesis>.json` with the settings and the sha256 of every model file.

| hypothesis | scored_at | freeze_commit | deviation |
|---|---|---|---|
| P4a | 2026-11-12 08:34 | 1a3aff90747d2cb9df4b468fa5faabdaab0737fd |  |
| P4b | 2026-11-12 08:39 | 7a42da37747f66b178b5494c927de1b53172a11f |  |
| P4b | 2026-11-12 08:39 | 7a42da37747f66b178b5494c927de1b53172a11f | initial run crashed before any test event was scored (AttributeError in mask construction); repeated after the fix |
| P4c | 2026-11-12 08:41 | ab6239f47e17f165fa634a0a8677d823cb6f9b76 |  |
| P1 | 2026-11-12 08:41 | 1d2251103c6f727c82783f84ccd4d1583ccd68fe |  |
| P2 | 2026-11-12 08:42 | 505ac57f68d97878f3d22f95d8dbc687ebb34c41 |  |
| P3a | 2026-11-12 08:43 | 23015883aa0b56728d828d758271bd46f3f6517b |  |
| P3b | 2026-11-12 08:43 | 015e2b5a1af942640434ce08207c82f1b8136bb1 |  |
| P4c | 2026-11-12 08:53 | ab6239f47e17f165fa634a0a8677d823cb6f9b76 | repeat after fixing a closure bug in the recall-gain statistic; models, settings and alarms unchanged |
| P3b | 2026-11-12 08:55 | 015e2b5a1af942640434ce08207c82f1b8136bb1 | repeat after a failed write of results.json (concurrent writers); simulated cells read back from p3b_cells.csv |
| P4d | 2026-11-12 09:13 | 35f77661ac8cec352fa83cf8b4ef463ede8b10e3 |  |
