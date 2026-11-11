#requires -Version 7.0
<#
Run on a qualified POSIX host with PowerShell 7. This launcher does not issue
operator records or read a Windows user-store credential. All four model records
must share one canonical ledger, run ID, request/deadline envelope and run cap.
The existing Experiment 2 global ceiling is $15, including every model below.
Example (placeholders, not qualification):
  pwsh scripts/run_experiment2.ps1 -Authorization /private/qualified-records.json -Live
#>
param(
    [Parameter(Mandatory = $true)] [string] $Authorization,
    [string] $Out = 'runs/judge-new',
    [ValidateRange(0.000000001, 15)] [decimal] $MaxUsd = 15,
    [string] $Python = 'python',
    [switch] $Live
)

$ErrorActionPreference = 'Stop'
if (-not ($IsLinux -or $IsMacOS)) {
    throw 'The qualified paid client requires a POSIX host; Windows flag shims are refused.'
}
if (-not $Live) {
    throw 'Paid execution requires explicit -Live and an owner-private -Authorization record.'
}
$authorizationPath = (Resolve-Path -LiteralPath $Authorization).Path
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$jobs = @(
    @{ Label = 'deepseek'; Model = 'deepseek/deepseek-v4-flash-0731'; Shares = @('0', '0.2', '0.4'); Agents = 50; Conditions = @('hidden-cell', 'visible-cell') },
    @{ Label = 'gptoss'; Model = 'openai/gpt-oss-20b'; Shares = @('0', '0.2', '0.4'); Agents = 50; Conditions = @('hidden-cell', 'visible-cell') },
    @{ Label = 'gpt61sol'; Model = 'openai/gpt-6.1-sol'; Shares = @('0'); Agents = 12; Conditions = @('hidden-cell') },
    @{ Label = 'gemini4argon'; Model = 'google/gemini-4-argon'; Shares = @('0'); Agents = 12; Conditions = @('hidden-cell') }
)
$sharedModels = @($jobs | ForEach-Object { $_.Model })
$cap = $MaxUsd.ToString([Globalization.CultureInfo]::InvariantCulture)
foreach ($job in $jobs) {
    $arguments = @('scripts/judgement_experiment.py', '--label', $job.Label, '--model', $job.Model,
                   '--out', $Out, '--agents', [string]$job.Agents, '--cases', '48', '--max-usd', $cap,
                   '--authorization', $authorizationPath, '--live', '--shared-models') + $sharedModels +
                 @('--shares') + $job.Shares + @('--conditions') + $job.Conditions
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Experiment stopped after $($job.Label) (exit $LASTEXITCODE); retain receipts and reconcile before any new run."
    }
}
