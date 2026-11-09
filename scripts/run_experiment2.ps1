# Launch Experiment 2 runs in parallel (standalone path; see docs/report/JUDGEMENT_PLAN.md).
$ErrorActionPreference = 'Continue'
$env:OPENROUTER_API_KEY = [Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY', 'User')
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
New-Item -ItemType Directory -Force runs/judge-logs | Out-Null
$jobs = @(
  @('deepseek', 'deepseek/deepseek-v4-flash-0731', 'runs/judge', '0 0.2 0.4', 50, 'hidden-cell visible-cell', 4, 2000),
  @('gptoss', 'openai/gpt-oss-20b', 'runs/judge', '0 0.2 0.4', 50, 'hidden-cell visible-cell', 4, 2000),
  @('gpt61sol', 'openai/gpt-6.1-sol', 'runs/judge-frontier', '0', 12, 'hidden-cell', 9, 4000),
  @('gemini4argon', 'google/gemini-4-argon', 'runs/judge-frontier', '0', 12, 'hidden-cell', 9, 4000)
)
$procs = foreach ($j in $jobs) {
  $cmd = "scripts/judgement_experiment.py --label $($j[0]) --model $($j[1]) --out $($j[2]) --shares $($j[3]) --agents $($j[4]) --cases 48 --conditions $($j[5]) --max-usd $($j[6]) --max-tokens $($j[7])"
  Start-Process python -ArgumentList $cmd -NoNewWindow -PassThru -RedirectStandardOutput "runs/judge-logs/$($j[0]).out" -RedirectStandardError "runs/judge-logs/$($j[0]).err"
}
$procs | Wait-Process
foreach ($j in $jobs) { "== $($j[0])"; Get-Content "runs/judge-logs/$($j[0]).out"; Get-Content "runs/judge-logs/$($j[0]).err" -Tail 5 }
