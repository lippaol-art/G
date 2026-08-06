# Kanoniczna bramka lokalna — WRAPPER 1:1 dla PowerShell.
#
# TEN PLIK NIE JEST DRUGA DEFINICJA BRAMKI. Tresc bramki zyje wylacznie
# w `scripts/check_all.sh`, ktory z kolei musi odpowiadac
# `.github/workflows/ci.yml` krok w krok. Dwie niezalezne definicje
# rozjechalyby sie przy pierwszej zmianie i bramka przestalaby cokolwiek
# gwarantowac — a bramka, ktorej nie mozna ufac, jest gorsza niz jej brak,
# bo daje falszywe poczucie zielonego.
#
# Ten plik istnieje wylacznie po to, zeby na Windowsie nie trzeba bylo
# pamietac o `bash`.
#
# Uzycie:
#     .\scripts\check_all.ps1            # pelna bramka
#     .\scripts\check_all.ps1 --szybko   # bez bramki 5.6 i bez golden baseline

$ErrorActionPreference = "Stop"
$korzen = Split-Path -Parent $PSScriptRoot

$bash = Get-Command bash -ErrorAction SilentlyContinue
if (-not $bash) {
    Write-Host "Nie znaleziono `bash`." -ForegroundColor Red
    Write-Host "Bramka jest zdefiniowana w scripts/check_all.sh i celowo NIE jest"
    Write-Host "przepisywana na PowerShell — dwie definicje rozjechalyby sie."
    Write-Host ""
    Write-Host "Zainstaluj Git for Windows (zawiera bash) albo wlacz WSL,"
    Write-Host "a potem uruchom: bash scripts/check_all.sh"
    exit 1
}

& $bash.Source (Join-Path $korzen "scripts/check_all.sh") @args
exit $LASTEXITCODE
