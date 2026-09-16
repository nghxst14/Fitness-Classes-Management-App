# Levanta o site num endereco publico temporario, para o Sergio (ou outra
# pessoa) o poder abrir no telemovel dele, de qualquer rede.
#
# QUANDO USAR: so quando alguem de fora precisa mesmo de ver. Para trabalhar,
# usa o servidor normal (ver GUIA_COMANDOS.md) - e mais rapido, recarrega
# sozinho e nao expoe nada.
#
# Corre com as definicoes de PRODUCAO (DEBUG=False), de proposito: e o mesmo
# ambiente do Railway, e por isso serve de ensaio geral do deploy. Foi assim
# que se descobriu que sem o collectstatic todas as paginas davam erro 500.
#
# Uso:   .\scripts\demonstracao.ps1
# Fecha: carrega Enter na janela, ou Ctrl+C.

$ErrorActionPreference = "Stop"
$projeto = Split-Path -Parent $PSScriptRoot
Set-Location $projeto

$python = ".\venv\Scripts\python.exe"
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$logTunel = Join-Path $env:TEMP "restart-now-tunel.log"
$ficheiroChave = Join-Path $env:TEMP "restart-now-secret.txt"

if (-not (Test-Path $python)) {
  Write-Host "Nao encontrei o venv. Cria-o primeiro (ver GUIA_COMANDOS.md)." -ForegroundColor Red
  exit 1
}
if (-not (Test-Path $cloudflared)) {
  Write-Host "Falta o cloudflared. Instala com:" -ForegroundColor Red
  Write-Host "  winget install --id Cloudflare.cloudflared --source winget"
  exit 1
}

# A chave e guardada entre execucoes para as sessoes de quem estava a ver nao
# caducarem so por se ter reiniciado a demonstracao. E temporaria: a de
# producao vem das variaveis do Railway.
if (-not (Test-Path $ficheiroChave)) {
  & $python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" |
    Out-File $ficheiroChave -Encoding utf8 -NoNewline
}
$env:DJANGO_SECRET_KEY = Get-Content $ficheiroChave -Raw
$env:DJANGO_DEBUG = "False"
# O endereco do tunel e sorteado a cada arranque; o ponto inicial faz o Django
# aceitar qualquer subdominio de trycloudflare.com sem o ter de adivinhar.
$env:DJANGO_ALLOWED_HOSTS = ".trycloudflare.com,127.0.0.1,localhost"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "https://*.trycloudflare.com"

# Com DEBUG=False o settings.py EXIGE estas variaveis e recusa arrancar sem
# elas (de proposito: em producao, esquece-las seria mandar os alunos para o
# numero errado ou publicar uma politica de privacidade sem responsavel).
# Numa demonstracao nao ha nenhum mal em valores de exemplo - o que nao pode
# e o script rebentar. Os valores a serio vivem nas variaveis do Railway.
$env:SERGIO_WHATSAPP = "351939339857"          # numero de TESTE do Andre
$env:RGPD_RESPONSAVEL = "RESTART NOW (demonstracao)"
$env:RGPD_CONTACTO = "a definir com o Sergio"
$env:RGPD_PRAZO_ANOS = "3"

function Parar-Tudo {
  Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
  $c = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
  if ($c) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }
}

try {
  Parar-Tudo   # nao deixar restos de uma execucao anterior
  Start-Sleep -Seconds 1

  Write-Host "A preparar os ficheiros estaticos..." -ForegroundColor Cyan
  # Obrigatorio com DEBUG=False: o WhiteNoise serve os ficheiros com o nome
  # assinado, e sem este passo qualquer pagina rebenta com erro 500.
  & $python manage.py collectstatic --noinput | Out-Null

  Write-Host "A arrancar o servidor..." -ForegroundColor Cyan
  Start-Process -FilePath $python `
    -ArgumentList 'manage.py','runserver','0.0.0.0:8000','--noreload' -WindowStyle Hidden
  Start-Sleep -Seconds 5

  # Tres tentativas: acontece o tunel registar-se e o nome nunca chegar a ser
  # publicado. Nesse caso vale mais tentar outra vez do que esperar.
  $url = $null
  for ($tentativa = 1; $tentativa -le 3 -and -not $url; $tentativa++) {
    Write-Host "A abrir o tunel (tentativa $tentativa de 3)..." -ForegroundColor Cyan
    Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
    if (Test-Path $logTunel) { Remove-Item $logTunel -Force }
    Start-Process -FilePath $cloudflared `
      -ArgumentList 'tunnel','--url','http://localhost:8000','--logfile',$logTunel -WindowStyle Hidden

    $candidato = $null
    for ($i = 0; $i -lt 20 -and -not $candidato; $i++) {
      Start-Sleep -Seconds 2
      if (Test-Path $logTunel) {
        $m = (Select-String -Path $logTunel -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' `
              -AllMatches -ErrorAction SilentlyContinue).Matches.Value
        if ($m) { $candidato = $m | Select-Object -First 1 }
      }
    }
    if (-not $candidato) { continue }

    # So se anuncia o endereco depois de ele RESPONDER. Anunciar um endereco
    # que ainda nao funciona faz perder a confianca de quem esta do outro lado.
    for ($i = 0; $i -lt 15 -and -not $url; $i++) {
      Start-Sleep -Seconds 4
      try {
        if ((Invoke-WebRequest $candidato -UseBasicParsing -TimeoutSec 20).StatusCode -eq 200) {
          $url = $candidato
        }
      } catch { }
    }
  }

  if (-not $url) {
    Write-Host "Nao consegui abrir o tunel. Tenta outra vez daqui a pouco." -ForegroundColor Red
    Parar-Tudo
    exit 1
  }

  Write-Host ""
  Write-Host "  O SITE ESTA NO AR:" -ForegroundColor Green
  Write-Host "  $url" -ForegroundColor Green
  Write-Host ""
  Write-Host "  O endereco muda a cada arranque - manda este." -ForegroundColor Yellow
  Write-Host "  O painel de administracao fica acessivel a quem tenha o link:" -ForegroundColor Yellow
  Write-Host "  confirma que a password do admin e longa antes de o partilhares." -ForegroundColor Yellow
  Write-Host ""
  Read-Host "Carrega Enter para fechar tudo"
}
finally {
  Write-Host "A fechar o tunel e o servidor..." -ForegroundColor Cyan
  Parar-Tudo
  Write-Host "Fechado." -ForegroundColor Green
}
