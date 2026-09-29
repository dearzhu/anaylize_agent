#!/usr/bin/env bash
# 一键创建 Python 3.11 虚拟环境并安装依赖（Linux / macOS）。
# 用法：
#   ./setup_env.sh            # 仅建环境 + 装依赖
#   ./setup_env.sh --pull     # 额外拉取 Ollama 模型
set -euo pipefail

VENV_DIR=".venv"
PY=""

# 1) 定位 Python 3.11
if command -v python3.11 >/dev/null 2>&1; then
  PY="python3.11"
elif command -v python3 >/dev/null 2>&1 && python3 --version 2>&1 | grep -q "3\.11"; then
  PY="python3"
else
  echo "错误：未找到 Python 3.11，请先安装 https://www.python.org/downloads/" >&2
  exit 1
fi

echo "[1/4] 使用 $PY 创建虚拟环境 '$VENV_DIR' ..."
"$PY" -m venv "$VENV_DIR"

# 2) 激活并升级 pip
echo "[2/4] 激活虚拟环境并升级 pip ..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip

# 3) 安装依赖
echo "[3/4] 安装依赖 (requirements.txt) ..."
python -m pip install -r requirements.txt

# 4) 可选：拉取 Ollama 模型
if [ "${1:-}" = "--pull" ]; then
  echo "[4/4] 拉取 Ollama 模型 ..."
  if command -v ollama >/dev/null 2>&1; then
    ollama pull bge-m3
    ollama pull qwen2.5:7b
    ollama pull qwen2.5-vl:7b
    echo "提示：深度推理模型可手动执行 'ollama pull deepseek-r1:32b'"
  else
    echo "警告：未检测到 ollama，跳过模型拉取。请先安装并启动 Ollama。"
  fi
else
  echo "[4/4] 跳过 Ollama 模型拉取（加 --pull 可自动拉取）。"
fi

echo ""
echo "✅ 环境就绪。后续使用前请先激活："
echo "      source $VENV_DIR/bin/activate"
