FROM python:3.12-slim

WORKDIR /app

# 切换 Debian 源到国内镜像（USTC）
RUN sed -i 's|deb.debian.org|mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 系统依赖（包含 Playwright/Chromium 所需库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2t64 \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（使用国内 pip 镜像）
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    -r requirements.txt

# 安装 Playwright 及 Chromium 浏览器（用于微信公众号文章抓取）
RUN pip install --no-cache-dir playwright && \
    python -m playwright install chromium && \
    python -m playwright install-deps chromium

# 应用代码
COPY backend/ .

# 规则库数据
COPY wuxing_rules/ /app/wuxing_rules/

# 非 root 运行
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "60", \
     "--keep-alive", "5"]