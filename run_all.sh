#!/usr/bin/env bash
# 一键运行本项目全部演示脚本（macOS / Linux）。
# 用法：
#   bash run_all.sh
# 说明：
#   - 自动创建 .venv（Python 3.11）并安装依赖
#   - 通过 Ollama HTTP API 确认/拉取所需模型（bge-m3、qwen2.5:7b、qwen2.5vl:7b）
#   - 依次运行 seed_data / demo_financial / demo_rag / demo_orchestrator / demo_multiagent
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ---------- 1) 虚拟环境 ----------
if [ ! -d ".venv" ]; then
  echo "[setup] 未找到 .venv，创建虚拟环境（Python 3.11）..."
  python3.11 -m venv .venv
  .venv/bin/python -m pip install -U pip -q
  .venv/bin/python -m pip install -r requirements.txt
fi
PY=.venv/bin/python

# ---------- 2) Ollama 模型就绪（CLI 可能不在 PATH，统一走 HTTP API） ----------
ensure_model() {
  local name="$1"
  if curl -s -m 2 http://localhost:11434/api/tags \
     | grep -q "\"name\":\"${name}\""; then
    return 0
  fi
  echo "[ollama] 拉取模型 ${name} ...（首次较慢，可中断后重试）"
  curl -s -X POST http://localhost:11434/api/pull -d "{\"name\":\"${name}\"}" >/dev/null
}

if curl -s -m 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
  ensure_model "bge-m3"
  ensure_model "qwen2.5:7b"
  ensure_model "qwen2.5vl:7b"
else
  echo "[warn] 未检测到 Ollama 服务（http://localhost:11434）。"
  echo "[warn] RAG / 编排类脚本将在无 LLM 情况下降级运行。"
fi

# ---------- 3) 依次运行全部脚本 ----------
run() {
  echo
  echo "================================================================"
  echo ">>> $1"
  echo "================================================================"
  $PY "$1" || echo "[warn] $1 返回非零退出码（可能已降级）。"
}

run scripts/seed_data.py
run scripts/demo_financial.py
run scripts/demo_rag.py
run scripts/demo_ocr.py
run scripts/demo_orchestrator.py
run scripts/demo_multiagent.py

echo
echo "==================== 全部脚本执行完毕 ===================="
