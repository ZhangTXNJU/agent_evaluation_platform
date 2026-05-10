# Agent评估平台 - 停止所有服务

$jobs = Get-Job | Where-Object { $_.Name -in @("MockAgent", "Backend", "Frontend") }

if (-not $jobs) {
    Write-Host "没有运行中的服务" -ForegroundColor Yellow
    exit 0
}

Write-Host "正在停止服务..." -ForegroundColor Cyan
$jobs | ForEach-Object {
    Write-Host "  停止 $($_.Name) (Job ID: $($_.Id))..."
    $_ | Stop-Job -PassThru | Remove-Job -Force
}

Write-Host "所有服务已停止" -ForegroundColor Green
