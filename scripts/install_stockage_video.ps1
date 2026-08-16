# Installation du stockage vidéos de cours (Digital School)
# Usage (depuis la racine du projet) :
#   powershell -ExecutionPolicy Bypass -File .\scripts\install_stockage_video.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\install_stockage_video.ps1 -TestCloud

param(
    [switch]$TestCloud
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> Digital School — installation stockage vidéos" -ForegroundColor Cyan
Write-Host "Répertoire : $Root"

if (-not (Test-Path ".\.env") -and (Test-Path ".\.env.example")) {
    Copy-Item ".\.env.example" ".\.env"
    Write-Host "Fichier .env créé depuis .env.example (à personnaliser)." -ForegroundColor Yellow
}

Write-Host "==> Installation des dépendances Python..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "==> Migrations pedagogie..."
python manage.py migrate pedagogie

$cmd = @("manage.py", "installer_stockage_video")
if ($TestCloud) {
    $cmd += "--test-cloud"
}
Write-Host "==> Vérification stockage..."
python @cmd

Write-Host ""
Write-Host "Terminé. Les enseignants peuvent déposer des MP4/WebM dans les cours en ligne." -ForegroundColor Green
Write-Host "Cloud optionnel : renseigner AWS_* dans .env puis relancer avec -TestCloud." -ForegroundColor DarkGray
