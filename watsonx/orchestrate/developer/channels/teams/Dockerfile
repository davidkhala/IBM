FROM python:slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

# 先只拷贝依赖声明,利用 Docker 层缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

# 端口由运行时的 PORT 环境变量决定
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
