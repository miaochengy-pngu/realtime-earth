<#
  push-to-github.ps1 — One-shot script to push realtime-earth to GitHub.

  Usage (in PowerShell, in the project root):
    .\push-to-github.ps1
    .\push-to-github.ps1 -Public
    .\push-to-github.ps1 -RepoName "my-real-time-earth"

  What it does:
    1. Checks for git
    2. Asks for your GitHub username
    3. If gh CLI is available, uses `gh repo create` to create + push
    4. If not, instructs you to create the repo on github.com, then pushes
#>

[CmdletBinding()]
param(
    [switch]$Public = $true,
    [string]$RepoName = "realtime-earth",
    [string]$CommitMessage = "Initial commit: Realtime Earth v0.1.0"
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "  OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  WARN: $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  ERR: $msg" -ForegroundColor Red }

# 1. Check git
Write-Step "Checking prerequisites"
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Err "git is not installed. Install from https://git-scm.com/download/win"
    exit 1
}
Write-Ok "git $($git.Version)"

# 2. Get GitHub username
$username = gh api user --jq .login 2>$null
if ($username) {
    Write-Ok "Detected GitHub user via gh CLI: $username"
} else {
    $username = Read-Host "Enter your GitHub username"
    if (-not $username) { Write-Err "Username required."; exit 1 }
}

$visibility = if ($Public) { "public" } else { "private" }
$remoteUrl = "https://github.com/$username/$RepoName.git"

# 3. Init local repo
Write-Step "Initializing local git repository"
if (-not (Test-Path ".git")) {
    git init | Out-Null
    git branch -M main
    Write-Ok "Initialised empty git repo on branch 'main'"
} else {
    Write-Ok ".git already exists"
}

# 4. Stage + commit
Write-Step "Staging files"
git add .
$status = git status --short
if (-not $status) {
    Write-Warn "Nothing to commit (everything already committed)"
} else {
    Write-Ok "Staged: $($status.Count) files"
    git commit -m $CommitMessage
    Write-Ok "Committed"
}

# 5. Create remote + push
Write-Step "Setting up GitHub remote"

# Try gh CLI first
$gh = Get-Command gh -ErrorAction SilentlyContinue
if ($gh -and (gh auth status 2>$null)) {
    Write-Ok "gh CLI authenticated, creating repo via gh..."
    gh repo create $RepoName --$visibility --source=. --remote=origin --push
    if ($LASTEXITCODE -eq 0) {
        Write-Step "DONE"
        Write-Host "  Repo:  https://github.com/$username/$RepoName" -ForegroundColor Green
        Write-Host "  Clone: git clone $remoteUrl" -ForegroundColor Green
        exit 0
    } else {
        Write-Warn "gh repo create failed, falling back to manual creation"
    }
}

# Manual fallback: ask user to create empty repo on GitHub first
Write-Host ""
Write-Host "  gh CLI not available or not logged in." -ForegroundColor Yellow
Write-Host "  Please create an EMPTY repository at:" -ForegroundColor Yellow
Write-Host "    https://github.com/new" -ForegroundColor Cyan
Write-Host "    Name: $RepoName" -ForegroundColor Cyan
Write-Host "    Visibility: $visibility" -ForegroundColor Cyan
Write-Host "    DO NOT initialize with README, .gitignore, or license (we have them)" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter when done..."

git remote remove origin 2>$null
git remote add origin $remoteUrl
Write-Ok "Remote set: $remoteUrl"

Write-Step "Pushing to GitHub"
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Err "Push failed. Common fixes:"
    Write-Host "  - Make sure the repo exists at $remoteUrl"
    Write-Host "  - If you used SSH before, run: git remote set-url origin git@github.com:$username/$RepoName.git"
    exit 1
}

Write-Step "DONE"
Write-Host "  Repo:  https://github.com/$username/$RepoName" -ForegroundColor Green
Write-Host "  Clone: git clone $remoteUrl" -ForegroundColor Green
