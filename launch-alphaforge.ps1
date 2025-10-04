<#
Launch AlphaForge (backend + frontend) with one PowerShell command.

Prerequisites:
 - Python & Poetry environment installed (run `poetry install` once)
 - Node.js & npm installed (run `npm install` inside alphaforge-mind once)

Usage:
  ./launch-alphaforge.ps1
or double-click in Explorer (may need to unblock script execution policy).

If execution is blocked, run (once, in an elevated PowerShell):
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

This wrapper simply invokes: poetry run launch-alphaforge
#>
param()

Write-Host "Launching AlphaForge..." -ForegroundColor Cyan

if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
  Write-Error "Poetry not found. Install from https://python-poetry.org/docs/"
  exit 1
}

poetry run launch-alphaforge
