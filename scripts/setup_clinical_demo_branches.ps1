[CmdletBinding()]
param(
    [string]$Base = "main",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$unsafeBranch = "demo/sepsis-unsafe"
$safeBranch = "demo/sepsis-safe"
$modelPath = "demo_repo/models/patient_labs.sql"

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    & git -C $root @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

$dirty = & git -C $root status --porcelain
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect Git worktree status."
}
if ($dirty) {
    throw "Refusing to create demo branches: the worktree is dirty."
}

$startingBranch = (& git -C $root symbolic-ref --quiet --short HEAD)
if ($LASTEXITCODE -ne 0 -or -not $startingBranch) {
    throw "Refusing to create demo branches from a detached HEAD."
}

Invoke-Git rev-parse --verify "$Base^{commit}" | Out-Null

try {
    Invoke-Git switch $Base

    $branches = @(
        @{
            Name = $unsafeBranch
            Fixture = Join-Path $root "tests/fixtures/patient_labs_unsafe.sql"
            Message = "demo: unsafe sepsis input change"
        },
        @{
            Name = $safeBranch
            Fixture = Join-Path $root "tests/fixtures/patient_labs_safe.sql"
            Message = "demo: safe additive clinical change"
        }
    )

    foreach ($branch in $branches) {
        & git -C $root show-ref --verify --quiet "refs/heads/$($branch.Name)"
        if ($LASTEXITCODE -eq 0 -and -not $Force) {
            throw "Local branch '$($branch.Name)' already exists. Re-run with -Force to recreate it."
        }
        if (-not (Test-Path -LiteralPath $branch.Fixture -PathType Leaf)) {
            throw "Fixture not found: $($branch.Fixture)"
        }
    }

    $activeBranch = $null
    foreach ($branch in $branches) {
        & git -C $root show-ref --verify --quiet "refs/heads/$($branch.Name)"
        if ($LASTEXITCODE -eq 0) {
            Invoke-Git branch --delete --force $branch.Name
        }

        Invoke-Git switch --create $branch.Name $Base
        $activeBranch = $branch.Name
        Copy-Item -LiteralPath $branch.Fixture -Destination (Join-Path $root $modelPath)
        Invoke-Git add -- $modelPath
        Invoke-Git commit -m $branch.Message
        Invoke-Git switch $Base
        $activeBranch = $null
    }
}
finally {
    $failedBranch = $activeBranch
    if ($activeBranch) {
        & git -C $root restore --source HEAD --staged --worktree -- $modelPath
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to clean target file '$modelPath' on '$activeBranch'."
        }
    }
    $currentBranch = (& git -C $root symbolic-ref --quiet --short HEAD)
    if ($LASTEXITCODE -ne 0 -or $currentBranch -ne $startingBranch) {
        & git -C $root switch $startingBranch
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to restore starting branch '$startingBranch'."
        }
    }
    if ($failedBranch -and $failedBranch -ne $startingBranch) {
        & git -C $root branch --delete --force $failedBranch
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to remove incomplete branch '$failedBranch'."
        }
    }
}
