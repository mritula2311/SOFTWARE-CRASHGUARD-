# Windows equivalent of `make all` (make is not installed here). Run from the repo root in PowerShell.
#   .\scripts\run_all.ps1           run every step in order
#   .\scripts\run_all.ps1 -Clean    delete every generated output first (results, tables, figures, processed data, build, reports), then run
# The last step (check_results) fails loudly if a result the report cites is missing or NOT_RUN without a stated reason.
param([switch]$Clean)
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "src"
$py = ".\.venv\Scripts\python"

if ($Clean) {
  foreach ($p in @("results\results.json", "results\tables", "results\figures", "data\processed", "build", "report\software_results.md", "data\processed\win_train.npz", "data\processed\win_validation.npz", "data\processed\win_test.npz", "results\paper", "report\novelty_summary.md",
                   "firmware_export\crashguard_rf.h", "firmware_export\crashguard_rf_candidate.h", "firmware_export\benchmark_rf.ino", "firmware_export\severity.h")) {
    if (Test-Path $p) { Remove-Item -Recurse -Force $p; Write-Host "removed $p" }
  }
  New-Item -ItemType Directory -Force "results\figures", "results\tables" | Out-Null
}

$steps = @(
  @("-m","crashguard.env_record"),
  @("-m","crashguard.data"), @("-m","crashguard.features"), @("-m","crashguard.split"), @("-m","crashguard.models"),
  @("-m","crashguard.export_c"), @("-m","crashguard.attacks"), @("-m","crashguard.forgery"), @("-m","crashguard.lora"), @("-m","crashguard.delivery_sim"),
  @("-m","crashguard.severity_synth"), @("-m","crashguard.nhtsa"), @("-m","crashguard.severity_vzcrash"), @("-m","crashguard.severity_study"), @("-m","crashguard.saturation_study"), @("-m","crashguard.saturation_splits"), @("-m","crashguard.s4_n14"), @("-m","crashguard.export_severity"),
  @("-m","crashguard.detector_extra"), @("-m","crashguard.robustness"), @("-m","crashguard.replay_study"), @("-m","crashguard.trigger_aware"), @("-m","crashguard.scheduler_study"), @("-m","crashguard.prevalence"), @("-m","crashguard.windows_cache"), @("-m","crashguard.direction"), @("-m","crashguard.injury"), @("-m","crashguard.conformal"), @("-m","crashguard.s2_dedup"), @("-m","crashguard.s3_conformal"), @("-m","crashguard.early"), @("-m","crashguard.s6_early"), @("-m","crashguard.physical_scaling"), @("-m","crashguard.spoofing"), @("-m","crashguard.capacity"), @("-m","crashguard.s5_burst"), @("-m","crashguard.s9_conformal_dv"), @("-m","crashguard.s10_adaptive"), @("-m","crashguard.ua_conformal"), @("-m","crashguard.s11_sct"), @("-m","crashguard.s13_spaced_table"), @("-m","crashguard.sct_protocol"), @("-m","crashguard.protocol_check"),
  @("-m","crashguard.t1_equal_escalation"),@("-m","crashguard.t2_pareto"),@("-m","crashguard.t3_cost"),@("-m","crashguard.t4_clarify"),@("-m","crashguard.t5_strict"),@("-m","crashguard.t6_thresholds"),@("-m","crashguard.t7_conformal_variants"),@("-m","crashguard.t8_sweep"),@("-m","crashguard.t9_ablations"),@("-m","crashguard.t10_airtime"),@("-m","crashguard.attacks_extra"),@("-m","crashguard.protocol_check_ext"),@("-m","crashguard.t13_second_dataset"),@("-m","crashguard.stats_audit"),@("-m","crashguard.paper_tables"),@("-m","crashguard.v2_a_study"),@("-m","crashguard.v2_d_study"),@("-m","crashguard.v2_b_study"),@("-m","crashguard.v2_b_sens"),@("-m","crashguard.v2_e_study"),@("-m","crashguard.v2_f_study"),@("-m","crashguard.v2_verdicts"),@("-m","crashguard.v2_docs"),@("-m","crashguard.v2_paper_tables"),
  @("-m","crashguard.t13_harvest"),@("-m","crashguard.t13_heldout"),@("-m","crashguard.t13_neardup"),@("-m","crashguard.sel_study"),@("-m","crashguard.sel_tables"),@("-m","crashguard.vz_audit"),@("-m","crashguard.vz_leakage"),@("-m","crashguard.vz_docs"),@("-m","crashguard.x_common"),@("-m","crashguard.x1_fixedpoint"),@("-m","crashguard.x2_cascade"),@("-m","crashguard.x3_groupaware"),@("-m","crashguard.x4_labels"),@("-m","crashguard.x5_rank"),@("-m","crashguard.x6_anchored"),@("-m","crashguard.x7_fusion"),@("-m","crashguard.x8_sequential"),@("-m","crashguard.x_verdicts"),@("-m","crashguard.jp_paper_tables"),
  @("@@c_checks"), @("merge/ingest_hardware.py"), @("-m","crashguard.attack_doc"), @("-m","crashguard.report"), @("-m","crashguard.novelty"), @("-m","crashguard.vzcrash_email"), @("-m","crashguard.compliance"), @("-m","crashguard.claim_table"), @("-m","crashguard.docs_gen"), @("-m","crashguard.repro_table"),
  @("-m","crashguard.jp_docs"), @("-m","crashguard.r_docs"), @("scripts/doc_headers.py"), @("-m","crashguard.check_results"))
foreach ($step in $steps) {
  Write-Host ">>> $($step -join " ")"
  if ($step[0] -eq "@@c_checks") {
    # C equivalence checks outside Windows: build the bundles, run scripts/c_checks.sh with gcc under WSL if it is installed, merge the JSON (a failing check is recorded, not fatal)
    & $py -m crashguard.c_bundle; if ($LASTEXITCODE -ne 0) { throw "c_bundle failed" }
    & $py -m crashguard.c_bundle --real; if ($LASTEXITCODE -ne 0) { throw "c_bundle --real failed" }
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
      $wd = (wsl wslpath -a ((Get-Location).Path -replace "\\", "/")) | Select-Object -First 1
      wsl bash -c "cd '$wd' && bash scripts/c_checks.sh build/c_checks_wsl.json"
      if (Test-Path build\c_checks_wsl.json) { & $py -m crashguard.merge_c_checks build\c_checks_wsl.json --label wsl2_ubuntu_gcc }
    } else { Write-Host "WSL not available: the C checks outside Windows are NOT_RUN on this machine" }
    continue
  }
  & $py @step
  if ($LASTEXITCODE -ne 0) { throw "step failed: $($step -join " ")" }
}
Write-Host "done"
