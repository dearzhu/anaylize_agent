<#
 .SYNOPSIS
    一键创建 Python 3.11 虚拟环境并安装项目依赖。
 .DESCRIPTION
    1) 定位系统中的 Python 3.11（优先用 'py -3.11' 启动器，否则回退到 python3.11/python）
    2) 在 .venv 创建虚拟环境
    3) 升级 pip 并安装 requirements.txt
    4) 可选：拉取 Ollama 模型（需本机已安装并运行 Ollama）
 .PARAMETER PullModels
    附加此开关会自动拉取所需 Ollama 模型（bge-m3 / qwen2.5:7b / qwen2.5-vl:7b）。
 .EXAMPLE
    powershell -ExecutionPolicy Bypass -File setup_env.ps1
    powershell -ExecutionPolicy Bypass -File setup_env.ps1 -PullModels
#>
param([switch]$PullModels)

$ErrorActionPreference = "Stop"
$venvDir = ".venv"
$py = $null

# ---- 1) 定位 Python 3.11 ----
if (Get-Command py -ErrorAction SilentlyContinue) {
    $ver = & py -3.11 --version 2>&1
    if ($ver -match "3\.11") { $py = "py -3.11" }
}
if (-not $py) {
    foreach ($c in @("python3.11", "python311", "python")) {
        if (Get-Command $c -ErrorAction SilentlyContinue) {
            $v = & $c --version 2>&1
            if ($v -match "3\.11") { $py = $c; break }
        }
    }
}
if (-not $py) {
    Write-Error "未找到 Python 3.11。请先安装 Python 3.11 (https://www.python.org/downloads/)，" +
                "并确保在安装时勾选 'Add to PATH' 与 'Install py launcher'。"
    exit 1
}
Write-Host "[1/4] 使用 $py 创建虚拟环境 '$venvDir' ..." -ForegroundColor Cyan
& $py -m venv $venvDir

# ---- 2) 激活并升级 pip ----
Write-Host "[2/4] 激活虚拟环境并升级 pip ..." -ForegroundColor Cyan
& "$venvDir/Scripts/Activate.ps1"
python -m pip install --upgrade pip

# ---- 3) 安装依赖 ----
Write-Host "[3/4] 安装依赖 (requirements.txt) ..." -ForegroundColor Cyan
python -m pip install -r requirements.txt

# ---- 4) 可选：拉取 Ollama 模型 ----
if ($PullModels) {
    Write-Host "[4/4] 拉取 Ollama 模型 ..." -ForegroundColor Cyan
    if (Get-Command ollama -ErrorAction SilentlyContinue) {
        ollama pull bge-m3
        ollama pull qwen2.5:7b
        ollama pull qwen2.5-vl:7b
        Write-Host "提示：如需深度推理模型可手动执行 'ollama pull deepseek-r1:32b'" -ForegroundColor Yellow
    } else {
        Write-Warning "未检测到 ollama 命令，跳过模型拉取。请先安装并启动 Ollama：https://ollama.com/"
    }
} else {
    Write-Host "[4/4] 跳过 Ollama 模型拉取（如需自动拉取请加 -PullModels）。" -ForegroundColor Cyan
}

Write-Host "`n✅ 环境就绪。后续使用前请先激活：" -ForegroundColor Green
Write-Host "      .venv/Scripts/Activate.ps1" -ForegroundColor White
