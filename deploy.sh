#!/bin/bash
# Meta-Skill.org 一键部署脚本
# 在项目根目录执行: bash deploy.sh

set -e

SERVER_IP="121.41.215.36"
SERVER_USER="root"
DEPLOY_DIR="/opt/meta-skill"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Meta-Skill.org 部署 ==="
echo "服务器: ${SERVER_USER}@${SERVER_IP}"
echo "部署目录: ${DEPLOY_DIR}"
echo ""

# 1. 打包项目（排除不需要的文件）
echo "[1/5] 打包项目文件..."
cd "$PROJECT_DIR"
tar czf /tmp/meta-skill-deploy.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.trae' \
    --exclude='*.zip' \
    --exclude='test_*' \
    --exclude='deploy.sh' \
    docker-compose.yml \
    .env.example \
    .dockerignore \
    backend/ \
    frontend/ \
    deploy/ \
    wuxing_rules/rules/ \
    wuxing_rules/wuxing_dsl.py \
    wuxing_rules/wuxing_engine.py

echo "  打包完成: $(du -h /tmp/meta-skill-deploy.tar.gz | cut -f1)"

# 2. 上传到服务器
echo "[2/5] 上传到服务器..."
ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${DEPLOY_DIR}"
scp /tmp/meta-skill-deploy.tar.gz ${SERVER_USER}@${SERVER_IP}:${DEPLOY_DIR}/

# 3. 解压 + 目录准备
echo "[3/5] 解压并准备目录..."
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /opt/meta-skill
tar xzf meta-skill-deploy.tar.gz
rm meta-skill-deploy.tar.gz

# 创建数据目录
mkdir -p /data/postgres /data/redis /data/backups /data/rule_libraries
mkdir -p deploy/certbot/www deploy/certbot/conf
mkdir -p deploy/nginx/conf.d
cp deploy/nginx/meta-skill.conf deploy/nginx/conf.d/meta-skill.conf

# 创建 .env（如果不存在）
if [ ! -f .env ]; then
    echo "⚠ 请先创建 .env 文件，参考 .env.example"
    cp .env.example .env
fi

echo "目录结构:"
ls -la /opt/meta-skill/
ENDSSH

# 4. 生成密钥
echo "[4/5] 生成安全密钥..."
SECRET_KEY=$(ssh ${SERVER_USER}@${SERVER_IP} "openssl rand -hex 32" 2>/dev/null || echo "请手动生成")
echo "  SECRET_KEY=${SECRET_KEY}"

# 5. 提示
echo ""
echo "=== 部署文件已上传 ==="
echo ""
echo "接下来请 SSH 登录服务器执行:"
echo ""
echo "  ssh ${SERVER_USER}@${SERVER_IP}"
echo "  cd ${DEPLOY_DIR}"
echo ""
echo "  # 编辑 .env，填入 SECRET_KEY 和 DB_PASSWORD"
echo "  nano .env"
echo ""
echo "  # 启动服务"
echo "  docker compose up -d"
echo ""
echo "  # 验证"
echo "  curl http://localhost/api/health"
echo ""
echo "=== 完成 ==="