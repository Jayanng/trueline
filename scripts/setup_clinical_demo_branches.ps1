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

$originalRefs = @{}
foreach ($branch in $branches) {
    $sha = (& git -C $root rev-parse --verify "refs/heads/$($branch.Name)^{commit}")
    if ($LASTEXITCODE -eq 0) {
        $originalRefs[$branch.Name] = $sha.Trim()
    }
    if ($originalRefs.ContainsKey($branch.Name) -and -not $Force) {
        throw "Local branch '$($branch.Name)' already exists. Re-run with -Force to recreate it."
    }
    if (-not (Test-Path -LiteralPath $branch.Fixture -PathType Leaf)) {
        throw "Fixture not found: $($branch.Fixture)"
    }
}

$activeBranch = $null
$succeeded = $false
try {
    Invoke-Git switch $Base
    foreach ($branch in $branches) {
        if ($originalRefs.ContainsKey($branch.Name)) {
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
    $succeeded = $true
}
finally {
    if (-not $succeeded -and $activeBranch) {
        & git -C $root restore --source HEAD --staged --worktree -- $modelPath
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to clean target file '$modelPath' on '$activeBranch'."
        }
    }
    $currentBranch = (& git -C $root symbolic-ref --quiet --short HEAD)
    if (-not $succeeded) {
        if ($LASTEXITCODE -ne 0 -or $currentBranch -ne $Base) {
            & git -C $root switch $Base
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to switch to base branch '$Base' for ref restoration."
            }
        }
        foreach ($branch in $branches) {
            if ($originalRefs.ContainsKey($branch.Name)) {
                & git -C $root update-ref "refs/heads/$($branch.Name)" $originalRefs[$branch.Name]
            }
            else {
                & git -C $root update-ref -d "refs/heads/$($branch.Name)"
            }
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to restore target ref '$($branch.Name)'."
            }
        }
    }
    $currentBranch = (& git -C $root symbolic-ref --quiet --short HEAD)
    if ($LASTEXITCODE -ne 0 -or $currentBranch -ne $startingBranch) {
        & git -C $root switch $startingBranch
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to restore starting branch '$startingBranch'."
        }
    }
}
