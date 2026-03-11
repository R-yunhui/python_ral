# ========== 阶段 1：用 uv 导出 requirements.txt ==========
FROM python:3.12-slim AS uv-export
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml .
COPY uv.lock .
RUN uv export --format=requirements-txt --frozen --no-dev -o requirements.txt

# ========== 阶段 2：最终运行镜像 ==========
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# 从阶段 1 拷出 uv 导出的 requirements.txt
COPY --from=uv-export /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "-m", "bisheng_generator.api"]