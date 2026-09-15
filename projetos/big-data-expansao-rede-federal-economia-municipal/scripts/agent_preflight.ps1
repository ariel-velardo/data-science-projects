$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

$VENV_PYTHON = Join-Path $ROOT ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "============================================================"
Write-Host "PROJECT PREFLIGHT"
Write-Host "============================================================"

Write-Host ""
Write-Host "Project:"
Write-Host (Get-Location)

Write-Host ""
Write-Host "Branch:"
git branch --show-current

Write-Host ""
Write-Host "HEAD:"
git rev-parse HEAD

Write-Host ""
Write-Host "origin/main:"
git rev-parse origin/main

Write-Host ""
Write-Host "Git status - project scope:"
git status --short -- .

Write-Host ""
Write-Host "Python environment:"

if (Test-Path $VENV_PYTHON) {
    Write-Host "[OK] Project .venv found"
    & $VENV_PYTHON -c "import sys; print(sys.executable)"
}
else {
    Write-Host "[ERROR] Project .venv not found:"
    Write-Host $VENV_PYTHON
    exit 1
}

Write-Host ""
Write-Host "pip check:"
& $VENV_PYTHON -m pip check

Write-Host ""
Write-Host "Playbooks:"

$files = @(
    "docs\playbooks\PLAYBOOK_PROJETO.md",
    "docs\playbooks\PLAYBOOK_CEMPRE.md",
    "docs\playbooks\PLAYBOOK_TERRITORIO.md",
    "docs\playbooks\PLAYBOOK_AUDITORIA.md",
    "docs\playbooks\ESTADO_ATUAL.md",
    "CLAUDE.md",
    "AGENTS.md"
)

$missing = @()

foreach ($file in $files) {
    $path = Join-Path $ROOT $file

    if (Test-Path $path) {
        Write-Host "[OK] $file"
    }
    else {
        Write-Host "[MISSING] $file"
        $missing += $file
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "[ERROR] One or more required playbooks are missing."
    exit 1
}

Write-Host ""
Write-Host "============================================================"
Write-Host "PREFLIGHT COMPLETED - READ ONLY"
Write-Host "============================================================"
