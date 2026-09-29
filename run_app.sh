#!/usr/bin/env bash
# 启动前端调用后端服务（FastAPI + 单页前端）。
# 用法： bash run_app.sh
# 然后浏览器访问 http://localhost:8000/
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# 1) 虚拟环境
if [ ! -d ".venv" ]; then
  echo "[setup] 未找到 .venv，创建虚拟环境（Python 3.11）..."
  python3.11 -m venv .venv
  .venv/bin/python -m pip install -U pip -q
  .venv/bin/python -m pip install -r requirements.txt
fi
PY=.venv/bin/python

# 2) 确保 Ollama 模型就绪（CLI 可能不在 PATH，统一走 HTTP API）
ensure_model() {
  local name="$1"
  if curl -s -m 2 http://localhost:11434/api/tags | grep -q "\"name\":\"${name}\""; then
    return 0
  fi
  echo "[ollama] 拉取模型 ${name} ..."
  curl -s -X POST http://localhost:11434/api/pull -d "{\"name\":\"${name}\"}" >/dev/null
}
if curl -s -m 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
  ensure_model "bge-m3"
  ensure_model "qwen2.5:7b"
else
  echo "[warn] 未检测到 Ollama 服务（http://localhost:11434），RAG / 报告类功能将降级。"
fi

# 3) 启动服务
echo "===== 启动服务： http://localhost:8000/ ====="
exec $PY -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
