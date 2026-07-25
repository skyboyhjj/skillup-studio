import paramiko, sys, time

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"
DEPLOY_DIR = "/opt/meta-skill"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=15, banner_timeout=10)
    print("connected\n")
    
    # Step 1: Install certbot
    print("--- 1/5 安装 certbot ---")
    _, stdout, stderr = ssh.exec_command(
        "apt-get update -qq && apt-get install -y -qq certbot 2>&1 | tail -5",
        timeout=120
    )
    print(stdout.read().decode().strip())
    err = stderr.read().decode().strip()
    if err and 'WARNING' not in err:
        print(f"ERR: {err[:300]}")
    
    # Verify
    _, stdout, _ = ssh.exec_command("certbot --version 2>&1")
    print(stdout.read().decode().strip())
    
    # Step 2: Create webroot dirs
    print("\n--- 2/5 创建 webroot 目录 ---")
    for cmd in [
        f"mkdir -p {DEPLOY_DIR}/deploy/certbot/www/.well-known/acme-challenge",
        f"mkdir -p {DEPLOY_DIR}/deploy/certbot/conf",
        f"mkdir -p {DEPLOY_DIR}/deploy/certbot/logs",
        "echo 'certbot test' > /opt/meta-skill/deploy/certbot/www/.well-known/acme-challenge/test",
    ]:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        err = stderr.read().decode().strip()
        if err: print(f"  ERR: {err[:200]}")
    
    print("  webroot 目录已创建")
    
    # Step 3: Update Nginx config to serve ACME challenges
    print("\n--- 3/5 更新 Nginx 配置（添加 ACME challenge） ---")
    
    # Read current config
    sftp = ssh.open_sftp()
    with sftp.file(f"{DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf", 'r') as f:
        conf = f.read()
    
    # Add ACME location block to each server block
    # Insert after "listen 80;" in each server block
    import re
    
    # Add ACME challenge location block
    acme_block = """
    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
"""
    
    # Insert after each "listen 80" line in server blocks
    lines = conf.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        if line.strip() == 'listen 80;' or line.strip() == 'listen 80 default_server;':
            # Check if next line already has the acme block
            next_line = lines[i+1] if i+1 < len(lines) else ''
            if 'acme-challenge' not in next_line:
                new_lines.append(acme_block)
    
    new_conf = '\n'.join(new_lines)
    
    with sftp.file(f"{DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf", 'w') as f:
        f.write(new_conf)
    sftp.close()
    print("  Nginx 配置已更新")
    
    # Step 4: Reload Nginx
    print("\n--- 4/5 重载 Nginx ---")
    _, stdout, stderr = ssh.exec_command("docker exec ms-nginx nginx -t 2>&1", timeout=10)
    print(stdout.read().decode().strip())
    err = stderr.read().decode().strip()
    if err: print(f"ERR: {err[:200]}")
    
    ssh.exec_command("docker exec ms-nginx nginx -s reload 2>&1", timeout=10)
    time.sleep(2)
    
    # Test ACME challenge
    _, stdout, _ = ssh.exec_command("curl -s -o /dev/null -w 'HTTP %{http_code}' http://localhost/.well-known/acme-challenge/test", timeout=10)
    code = stdout.read().decode().strip()
    print(f"  ACME challenge test: {code}")
    
    # Step 5: Create certbot deploy script
    print("\n--- 5/5 创建 SSL 签发脚本 ---")
    
    cert_script = f'''#!/bin/bash
# SSL 证书签发脚本
# 使用前确保 DNS 已指向本服务器: 121.41.215.36
# 运行: bash /opt/meta-skill/ssl-issue.sh

set -e

DEPLOY_DIR="{DEPLOY_DIR}"
DOMAINS=("meta-skill.org" "www.meta-skill.org" "hui-skill.cn" "www.hui-skill.cn")

echo "=== SSL 证书签发 ==="
echo ""

# 检查 DNS
for d in "{{DOMAINS[@]}}"; do
    echo -n "检查 $d DNS... "
    IP=$(dig +short "$d" 2>/dev/null | tail -1)
    if [ "$IP" = "121.41.215.36" ]; then
        echo "OK ($IP)"
    else
        echo "FAIL (当前: $IP)"
        echo "  请先将 $d 的 A 记录指向 121.41.215.36"
        exit 1
    fi
done

echo ""
echo "DNS 全部就绪，开始签发证书..."

# 签发 meta-skill.org
certbot certonly --webroot \\
    -w /opt/meta-skill/deploy/certbot/www \\
    -d meta-skill.org -d www.meta-skill.org \\
    --email admin@meta-skill.org \\
    --agree-tos --no-eff-email \\
    --keep-until-expiring

# 签发 hui-skill.cn
certbot certonly --webroot \\
    -w /opt/meta-skill/deploy/certbot/www \\
    -d hui-skill.cn -d www.hui-skill.cn \\
    --email admin@hui-skill.cn \\
    --agree-tos --no-eff-email \\
    --keep-until-expiring

echo ""
echo "证书签发完成！现在启用 SSL 配置..."

# 此时需要手动替换 Nginx 配置为 SSL 版本
# 详见: /opt/meta-skill/deploy/nginx/conf.d/meta-skill-ssl.conf
echo "下一步: 运行 ssl-enable.sh 启用 HTTPS"
'''
    
    sftp = ssh.open_sftp()
    with sftp.file(f"{DEPLOY_DIR}/ssl-issue.sh", 'w') as f:
        f.write(cert_script)
    ssh.exec_command(f"chmod +x {DEPLOY_DIR}/ssl-issue.sh")
    sftp.close()
    print("  ssl-issue.sh 已创建")
    
    # Now create SSL-enabled Nginx config
    ssl_nginx_conf = '''upstream api_backend {
    server api:8000;
}

# ============================================================
# meta-skill.org — 体验展示 + 开源发布
# ============================================================
server {
    listen 80;
    server_name meta-skill.org www.meta-skill.org;

    # ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 其他请求重定向到 HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name meta-skill.org www.meta-skill.org;

    ssl_certificate /etc/letsencrypt/live/meta-skill.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/meta-skill.org/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 根路径
    location = / {
        return 302 /studio/;
    }

    location /studio/ {
        alias /usr/share/nginx/html/studio/;
        try_files $uri $uri/ /studio/index.html;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location /studio/rules/ {
        alias /usr/share/nginx/html/rules/;
        try_files $uri $uri/ /studio/rules/index.html;
        expires 1d;
    }

    location /studio/community/ {
        alias /usr/share/nginx/html/community/;
        try_files $uri $uri/ /studio/community/index.html;
        expires 1d;
    }

    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Domain-Role demo;
        proxy_read_timeout 120s;
        proxy_buffering off;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml+rss;
    gzip_min_length 256;
    gzip_comp_level 5;
    gzip_vary on;
}

# ============================================================
# hui-skill.cn — 数据标注 + 规则库创建
# ============================================================
server {
    listen 80;
    server_name hui-skill.cn www.hui-skill.cn;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name hui-skill.cn www.hui-skill.cn;

    ssl_certificate /etc/letsencrypt/live/hui-skill.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hui-skill.cn/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location = / {
        return 302 /annotate/;
    }

    location /annotate/ {
        alias /usr/share/nginx/html/annotate/;
        index index.html;
        try_files $uri /annotate/index.html;
    }

    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Domain-Role full;
        proxy_read_timeout 120s;
        proxy_buffering off;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml+rss;
    gzip_min_length 256;
    gzip_comp_level 5;
    gzip_vary on;
}

# ============================================================
# IP 直连（仅 HTTP，无 SSL）
# ============================================================
server {
    listen 80 default_server;
    server_name _;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location = / {
        return 302 /studio/;
    }

    location /studio/ {
        alias /usr/share/nginx/html/studio/;
        try_files $uri $uri/ /studio/index.html;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location /studio/rules/ {
        alias /usr/share/nginx/html/rules/;
        try_files $uri $uri/ /studio/rules/index.html;
    }

    location /studio/community/ {
        alias /usr/share/nginx/html/community/;
        try_files $uri $uri/ /studio/community/index.html;
    }

    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Domain-Role demo;
        proxy_read_timeout 120s;
        proxy_buffering off;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml+rss;
    gzip_min_length 256;
    gzip_comp_level 5;
    gzip_vary on;
}
'''

    sftp = ssh.open_sftp()
    with sftp.file(f"{DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill-ssl.conf", 'w') as f:
        f.write(ssl_nginx_conf)
    sftp.close()
    print("  meta-skill-ssl.conf 已创建（SSL 版 Nginx 配置）")
    
    # Create SSL enable script
    enable_script = f'''#!/bin/bash
# 启用 SSL 配置
# 运行: bash /opt/meta-skill/ssl-enable.sh

set -e

DEPLOY_DIR="{DEPLOY_DIR}"

echo "=== 启用 SSL 配置 ==="

# 备份当前配置
cp {DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf {DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf.bak
echo "已备份当前配置"

# 替换为 SSL 配置
cp {DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill-ssl.conf {DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf
echo "已启用 SSL 配置"

# 更新 Nginx 挂载（添加证书目录）
cd {DEPLOY_DIR}

# 修改 docker-compose.yml 添加 letsencrypt 卷挂载
if ! grep -q "letsencrypt" docker-compose.yml; then
    echo "请在 docker-compose.yml 的 nginx volumes 中添加:"
    echo "  - /etc/letsencrypt:/etc/letsencrypt:ro"
    echo "  - {DEPLOY_DIR}/deploy/certbot/www:/var/www/certbot:ro"
fi

# 测试配置
docker exec ms-nginx nginx -t

# 重载
docker exec ms-nginx nginx -s reload

echo ""
echo "SSL 已启用！"
echo "https://meta-skill.org/"
echo "https://hui-skill.cn/"
'''
    
    sftp = ssh.open_sftp()
    with sftp.file(f"{DEPLOY_DIR}/ssl-enable.sh", 'w') as f:
        f.write(enable_script)
    ssh.exec_command(f"chmod +x {DEPLOY_DIR}/ssl-enable.sh")
    sftp.close()
    print("  ssl-enable.sh 已创建")
    
    # Set up certbot auto-renewal cron
    print("\n--- 设置自动续期 cron ---")
    ssh.exec_command(
        '(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook \'docker exec ms-nginx nginx -s reload\'") | crontab -',
        timeout=10
    )
    _, stdout, _ = ssh.exec_command("crontab -l 2>&1", timeout=10)
    print(f"  Cron: {stdout.read().decode().strip()}")
    
    print("\n=== SSL 准备完成 ===")
    print("\n当前状态:")
    print("  certbot: 已安装")
    print("  webroot: 已配置")
    print("  Nginx: 已添加 ACME challenge 路由")
    print("  SSL 配置: 已就绪（meta-skill-ssl.conf）")
    print("  自动续期: 已配置（每天凌晨 3 点）")
    print("\n待 DNS 配置完成后运行:")
    print("  ssh root@121.41.215.36")
    print("  bash /opt/meta-skill/ssl-issue.sh    # 签发证书")
    print("  bash /opt/meta-skill/ssl-enable.sh   # 启用 HTTPS")
    
    ssh.close()
    
except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()