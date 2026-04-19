Write-Host "🌐 Deixando o PromoMargem online via LocalTunnel..." -ForegroundColor Cyan

# Check if front-end is already running locally (port 3000)
Write-Host "Certifique-se de que o sistema foi iniciado via 'iniciar.ps1' primeiro." -ForegroundColor Yellow

Write-Host "🔗 Criando link público..." -ForegroundColor Green
npx localtunnel --port 3000
