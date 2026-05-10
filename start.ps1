# Agent评估平台 - 一键启动脚本
# 在新窗口中分别启动 Mock Agent + 后端 + 前端

$RootDir = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  Agent评估平台 - 一键启动" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

# ============ 环境检查 ============
$pythonOk = $true
$nodeOk = $true
try { python --version 2>&1 | Out-Null } catch { $pythonOk = $false }
try { node --version 2>&1 | Out-Null } catch { $nodeOk = $false }

if (-not $pythonOk) {
    Write-Host "[ERR] 未找到 Python，请安装 Python 3.11+" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}
if (-not $nodeOk) {
    Write-Host "[ERR] 未找到 Node.js，请安装 Node.js 18+" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}
Write-Host "[OK] Python: $(python --version 2>&1)" -ForegroundColor Green
Write-Host "[OK] Node.js: $(node --version 2>&1)" -ForegroundColor Green

# ============ 后端依赖安装 ============
Write-Host ""
Write-Host "[INFO] 检查后端环境..." -ForegroundColor Cyan

$BackendDir = "$RootDir\backend"
$VenvDir = "$BackendDir\venv"
$venvActivate = "$VenvDir\Scripts\activate.ps1"

if (-not (Test-Path "$VenvDir\Scripts\python.exe")) {
    Write-Host "[INFO] 创建 Python 虚拟环境..." -ForegroundColor Cyan
    python -m venv $VenvDir
    if (-not $?) {
        Write-Host "[ERR] 虚拟环境创建失败" -ForegroundColor Red
        Read-Host "按 Enter 退出"
        exit 1
    }
    Write-Host "[OK] 虚拟环境已创建" -ForegroundColor Green
}

# 激活 venv 并安装依赖
. $venvActivate
$needInstall = $false
try { python -c "import fastapi, uvicorn, sqlalchemy, httpx" 2>&1 | Out-Null } catch { $needInstall = $true }

if ($needInstall) {
    Write-Host "[INFO] 安装后端依赖..." -ForegroundColor Cyan
    python -m pip install -r "$BackendDir\requirements.txt" -q
    if (-not $?) {
        Write-Host "[ERR] 依赖安装失败" -ForegroundColor Red
        Read-Host "按 Enter 退出"
        exit 1
    }
    Write-Host "[OK] 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "[OK] 后端依赖已就绪" -ForegroundColor Green
}

# 初始化数据库
Write-Host "[INFO] 初始化数据库..." -ForegroundColor Cyan
Set-Location $BackendDir
python init_db.py 2>&1 | Out-Null
if (-not $?) {
    Write-Host "[ERR] 数据库初始化失败" -ForegroundColor Red
    Set-Location $RootDir
    Read-Host "按 Enter 退出"
    exit 1
}
Set-Location $RootDir
Write-Host "[OK] 数据库就绪" -ForegroundColor Green
deactivate

# ============ 前端依赖安装 ============
Write-Host ""
Write-Host "[INFO] 检查前端环境..." -ForegroundColor Cyan

$FrontendDir = "$RootDir\frontend"
if (-not (Test-Path "$FrontendDir\node_modules")) {
    Write-Host "[INFO] 安装前端依赖 (首次可能较慢)..." -ForegroundColor Cyan
    Set-Location $FrontendDir
    npm install
    if (-not $?) {
        Write-Host "[ERR] 前端依赖安装失败" -ForegroundColor Red
        Set-Location $RootDir
        Read-Host "按 Enter 退出"
        exit 1
    }
    Set-Location $RootDir
    Write-Host "[OK] 前端依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "[OK] 前端依赖已安装" -ForegroundColor Green
}

# ============ 启动服务 ============

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  启动各服务（将在新窗口中打开）" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# --- Mock Agent ---
$MockScript = "$RootDir\examples\mock_agent.py"
if (Test-Path $MockScript) {
    Write-Host "[INFO] 启动 Mock Agent (端口 9001)..." -ForegroundColor Cyan
    $proc1 = Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Write-Host '=== Mock Agent (端口 9001) ===' -ForegroundColor Cyan; python `"$MockScript`"; Read-Host"
    ) -PassThru
    Write-Host "[OK] Mock Agent 已启动 (PID: $($proc1.Id))" -ForegroundColor Green
} else {
    Write-Host "[WARN] 未找到 Mock Agent 脚本" -ForegroundColor Yellow
}

Start-Sleep -Seconds 1

# --- 后端 ---
Write-Host "[INFO] 启动后端 (端口 8001)..." -ForegroundColor Cyan
$proc2 = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Write-Host '=== 后端 FastAPI (端口 8001) ===' -ForegroundColor Cyan; & `"$venvActivate`"; Set-Location `"$BackendDir`"; python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload; Read-Host"
) -PassThru
Write-Host "[OK] 后端已启动 (PID: $($proc2.Id))" -ForegroundColor Green

Start-Sleep -Seconds 2

# --- 前端 ---
Write-Host "[INFO] 启动前端 (端口 5173)..." -ForegroundColor Cyan
$proc3 = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Write-Host '=== 前端 Vite (端口 5173) ===' -ForegroundColor Cyan; Set-Location `"$FrontendDir`"; npx vite --host --port 5173; Read-Host"
) -PassThru
Write-Host "[OK] 前端已启动 (PID: $($proc3.Id))" -ForegroundColor Green

# ============ 完成 ============
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  启动完成！等待几秒服务就绪..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  前端界面:  http://localhost:5173" -ForegroundColor White
Write-Host "  后端 API:  http://localhost:8001/docs" -ForegroundColor White
if (Test-Path $MockScript) {
    Write-Host "  Mock Agent: http://localhost:9001/docs" -ForegroundColor White
}
Write-Host ""
Write-Host "  关闭各窗口即可停止服务" -ForegroundColor Yellow
Write-Host ""

# 自动打开浏览器
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Read-Host "按 Enter 退出本脚本（不影响已启动的服务窗口）"
