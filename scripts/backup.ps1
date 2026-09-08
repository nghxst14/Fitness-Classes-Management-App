# Copia de seguranca dos dados: exporta utilizadores (com saldos), marcacoes,
# movimentos de creditos, aulas e configuracao para um ficheiro JSON datado.
#
# PORQUE JSON e nao um dump binario: e legivel. Podes abrir o ficheiro e ver
# os saldos com os teus olhos, o que num ficheiro binario nao consegues. E nao
# precisa do pg_dump instalado -- corre em Python puro, com o que ja tens.
#
# Uso:
#   .\scripts\backup.ps1                      # base de dados local (dev)
#   .\scripts\backup.ps1 -Producao            # a do Railway (le a DATABASE_URL)
#   .\scripts\backup.ps1 -Destino "D:\copias" # noutra pasta
#
# QUANDO CORRER:
#   - antes de qualquer operacao que apague coisas (limpar dados de teste,
#     migracoes, accoes em massa no admin);
#   - de tempos a tempos, quando houver creditos pagos a serio em jogo.
#
# ONDE FICA: por defeito numa pasta da OneDrive, se existir. Isso e de
# proposito -- uma copia guardada no mesmo disco que a base de dados nao te
# salva de o disco falhar, e uma copia guardada dentro do Railway nao te salva
# de perderes a conta do Railway.

param(
  [string]$Destino = "",
  [switch]$Producao
)

$ErrorActionPreference = "Stop"
$projeto = Split-Path -Parent $PSScriptRoot
Set-Location $projeto
$python = ".\venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  Write-Host "Nao encontrei o venv. Ver GUIA_COMANDOS.md." -ForegroundColor Red
  exit 1
}

# --- Onde guardar --------------------------------------------------------
if (-not $Destino) {
  if ($env:OneDrive -and (Test-Path $env:OneDrive)) {
    $Destino = Join-Path $env:OneDrive "RESTART NOW - copias"
  } else {
    $Destino = Join-Path $env:USERPROFILE "Documents\RESTART NOW - copias"
  }
}
if (-not (Test-Path $Destino)) { New-Item -ItemType Directory -Path $Destino -Force | Out-Null }

$carimbo = Get-Date -Format "yyyy-MM-dd_HHmm"
$ambiente = if ($Producao) { "producao" } else { "dev" }
$ficheiro = Join-Path $Destino "restart-now_${ambiente}_${carimbo}.json"

# --- Producao: e preciso a DATABASE_URL ----------------------------------
if ($Producao) {
  if (-not $env:DATABASE_URL) {
    Write-Host "Falta a variavel DATABASE_URL." -ForegroundColor Red
    Write-Host "Copia-a do Railway (separador Variables do PostgreSQL) e define-a"
    Write-Host "so nesta janela, antes de correr o script:" -ForegroundColor Yellow
    Write-Host '  $env:DATABASE_URL = "postgresql://..."'
    exit 1
  }
  Write-Host "A copiar da base de dados de PRODUCAO..." -ForegroundColor Yellow
} else {
  Write-Host "A copiar da base de dados local (dev)..." -ForegroundColor Cyan
}

# --- A exportacao --------------------------------------------------------
# So as nossas duas apps: e ai que estao os dados do negocio. Fica de fora o
# ruido do Django (sessoes, registos do admin, permissoes), que nao interessa
# guardar e ainda complica o restauro.
#
# O --natural-foreign faz as referencias a tabelas do Django (permissoes,
# tipos de conteudo) serem gravadas pelo nome em vez do numero. Sem isso, um
# restauro numa base de dados nova podia apontar para as linhas erradas,
# porque os numeros nao sao os mesmos.
#
# Duas armadilhas de codificacao, ambas descobertas a testar o restauro deste
# script -- e ambas invisiveis ate esse momento, porque a copia PARECE bem
# feita e so se revela imprestavel quando faz falta:
#
#  1. Nao usar "> ficheiro" nem Out-File: o PowerShell 5.1 escreve UTF-8 COM
#     BOM (os bytes EF BB BF no inicio) e o leitor de JSON do Django rejeita-o.
#     Dai o --output, que deixa o Django escrever o ficheiro.
#  2. O PYTHONUTF8 e preciso porque, no Windows, o Python abre os ficheiros na
#     codificacao do sistema (cp1252). Os "ç" e os acentos ficavam gravados
#     nessa codificacao e o restauro rebentava a le-los como UTF-8.
$env:PYTHONUTF8 = "1"
& $python manage.py dumpdata accounts bookings --natural-foreign --indent 2 `
  --output $ficheiro

if (-not (Test-Path $ficheiro) -or (Get-Item $ficheiro).Length -lt 100) {
  Write-Host "A copia saiu vazia ou demasiado pequena. NAO ficou guardada." -ForegroundColor Red
  if (Test-Path $ficheiro) { Remove-Item $ficheiro }
  exit 1
}

$kb = [math]::Round((Get-Item $ficheiro).Length / 1KB, 1)

# Em desenvolvimento guarda tambem o proprio ficheiro da base de dados: e uma
# fotografia exata e nao custa nada. Em producao nao existe (e PostgreSQL).
if (-not $Producao -and (Test-Path "db.sqlite3")) {
  Copy-Item "db.sqlite3" (Join-Path $Destino "restart-now_dev_${carimbo}.sqlite3")
}

Write-Host ""
Write-Host "  Copia guardada:" -ForegroundColor Green
Write-Host "  $ficheiro" -ForegroundColor Green
Write-Host "  $kb KB" -ForegroundColor Green
Write-Host ""
Write-Host "  Lembra-te: uma copia por testar nao e uma copia." -ForegroundColor Yellow
Write-Host "  Ve como testar um restauro no GUIA_COMANDOS.md (seccao 10)." -ForegroundColor Yellow

# Quantas copias ja la estao -- as antigas nao se apagam automaticamente
# (sao pequenas), mas convem saberes que estao a acumular.
$total = (Get-ChildItem $Destino -Filter "restart-now_*.json").Count
if ($total -gt 20) {
  Write-Host ""
  Write-Host "  Ja tens $total copias nessa pasta. Podes apagar as mais antigas." -ForegroundColor DarkGray
}
