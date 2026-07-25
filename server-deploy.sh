#!/bin/bash
# Meta-Skill.org 服务器端一键部署脚本
# 在服务器上执行: bash /opt/meta-skill/server-deploy.sh

set -e

DEPLOY_DIR="/opt/meta-skill"

echo "=== Meta-Skill.org 服务器端部署 ==="

# 1. 配置 Docker 镜像加速器（覆盖现有配置，因为默认源已失效）
echo "[1/7] 配置 Docker 镜像加速器..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'DOCKEREOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerhub.timeweb.cloud",
    "https://docker.1ms.run"
  ]
}
DOCKEREOF
systemctl restart docker
sleep 3
echo "  镜像加速器已更新为 DaoCloud"

# 2. 创建数据目录
echo "[2/7] 创建数据目录..."
mkdir -p /data/postgres /data/redis /data/backups /data/rule_libraries
mkdir -p ${DEPLOY_DIR}/deploy/certbot/www ${DEPLOY_DIR}/deploy/certbot/conf
mkdir -p ${DEPLOY_DIR}/deploy/nginx/conf.d

# 复制 Nginx 配置到 conf.d
cp ${DEPLOY_DIR}/deploy/nginx/meta-skill.conf ${DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf

# 3. 生成密钥
echo "[3/7] 生成安全密钥..."
if [ ! -f ${DEPLOY_DIR}/.env ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    cat > ${DEPLOY_DIR}/.env << EOF
# Meta-Skill.org 环境变量（自动生成）
SECRET_KEY=${SECRET_KEY}
DB_PASSWORD=${DB_PASSWORD}
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
CORS_ORIGINS=https://meta-skill.org,http://localhost:8088
LOG_LEVEL=INFO
EOF
    echo "  已生成 .env"
    echo "  SECRET_KEY=${SECRET_KEY}"
    echo "  DB_PASSWORD=${DB_PASSWORD}"
else
    echo "  .env 已存在，跳过"
fi

# 4. 检查 Docker 环境
echo "[4/7] 检查 Docker 环境..."
docker --version
docker compose version

# 验证镜像加速器生效
echo "  镜像源: $(docker info --format '{{range .RegistryConfig.Mirrors}}{{.}} {{end}}')"

# 5. 拉取基础镜像
echo "[5/7] 拉取基础镜像..."
for img in nginx:1.25-alpine postgres:16-alpine redis:7-alpine python:3.12-slim; do
    echo "  拉取 $img ..."
    docker pull $img
done

# 6. 构建并启动
echo "[6/7] 构建并启动服务..."
cd ${DEPLOY_DIR}
docker compose build api
docker compose up -d

# 7. 等待服务就绪
echo "[7/7] 等待服务就绪..."
sleep 10

echo ""
echo "=== 服务状态 ==="
docker compose ps

echo ""
echo "=== 健康检查 ==="
curl -s http://localhost/api/health || echo "  ⚠ API 尚未就绪，请等待 30 秒后重试 curl http://localhost/api/health"

echo ""
echo "=== 部署完成 ==="
echo ""
echo "后续步骤:"
echo "  1. 配置 DNS: meta-skill.org A 记录 → $(curl -s ifconfig.me || echo '服务器IP')"
echo "  2. 配置 SSL: certbot certonly --webroot ..."
echo "  3. 配置防火墙: 开放 80/443 端口"
echo "  4. 编辑 .env 填入 DEEPSEEK_API_KEY（可选）"
echo ""
echo "查看日志: docker compose logs -f api"