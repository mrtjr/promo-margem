Write-Host "Iniciando o PromoMargem..." -ForegroundColor Cyan

# Verificando se o Docker esta rodando
if (!(Get-Process docker -ErrorAction SilentlyContinue)) {
    Write-Host "AVISO: O Docker nao parece estar rodando. Por favor, abra o Docker Desktop primeiro." -ForegroundColor Yellow
    Write-Host "Pressione qualquer tecla para sair."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

Write-Host "Subindo os containers (isso pode levar alguns minutos na primeira vez)..." -ForegroundColor Green
docker-compose up -d --build

Write-Host "Tudo pronto!" -ForegroundColor Green
Write-Host "-------------------------------------------"
Write-Host "Painel do Gestor: http://localhost:3000" -ForegroundColor Blue
Write-Host "API (Backend):    http://localhost:8000" -ForegroundColor Blue
Write-Host "-------------------------------------------"
Write-Host "Pressione qualquer tecla para fechar esta janela."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
