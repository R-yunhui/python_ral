# ========== 阶段 1：用 uv 导出 requirements.txt ==========
FROM ac2-registry.cn-hangzhou.cr.aliyuncs.com/ac2/base:ubuntu24.04-py312 AS uv-export
RUN pip install --no-cache-dir uv -i https://mirrors.aliyun.com/pypi/simple
WORKDIR /app
COPY pyproject.toml .
COPY uv.lock .
RUN uv export --format=requirements-txt --frozen --no-dev -o requirements.txt

# ========== 阶段 2：阿里云 AC2 Python 3.12 + 阿里云 PyPI ==========
FROM ac2-registry.cn-hangzhou.cr.aliyuncs.com/ac2/base:ubuntu24.04-py312

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITECODE=1 \
    PYTHONPATH=/app/bisheng_generator
WORKDIR /app

# 日志目录，运行时挂载到宿主机：-v /宿主机/logs:/app/log
VOLUME ["/app/log"]

# 使用官方 Ubuntu 源，避免构建环境访问不到阿里云镜像
RUN echo 'deb http://archive.ubuntu.com/ubuntu noble main restricted universe multiverse' > /etc/apt/sources.list \
 && echo 'deb http://archive.ubuntu.com/ubuntu noble-updates main restricted universe multiverse' >> /etc/apt/sources.list \
 && echo 'deb http://archive.ubuntu.com/ubuntu noble-security main restricted universe multiverse' >> /etc/apt/sources.list \
 && rm -f /etc/apt/sources.list.d/*.list 2>/dev/null || true

RUN apt-get update -y \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY --from=uv-export /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

RUN apt-get update -y \
 && apt-get remove -y build-essential \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8000
CMD ["python3", "-m", "bisheng_generator.api"]