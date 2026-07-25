import paramiko, sys, time, re

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"
DEPLOY_DIR = "/opt/meta-skill"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=15, banner_timeout=10)
    print("connected\n")
    
    # Step 1: Update Nginx config with ACME challenge
    print("--- 1/4 更新 Nginx 配置（添加 ACME challenge） ---")
    sftp = ssh.open_sftp()
    with sftp.file(f"{DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf", 'r') as f:
        conf = f.read().decode('utf-8')
    
    acme_block = """
    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
"""
    
    lines = conf.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        if line.strip() in ('listen 80;', 'listen 80 default_server;'):
            next_line = lines[i+1] if i+1 < len(lines) else ''
            if 'acme-challenge' not in next_line:
                new_lines.append(acme_block)
    
    new_conf = '\n'.join(new_lines)
    
    with sftp.file(f"{DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf", 'w') as f:
        f.write(new_conf)
    sftp.close()
    print("  Nginx 配置已更新")
    
    # Test & reload
    _, stdout, stderr = ssh.exec_command("docker exec ms-nginx nginx -t 2>&1", timeout=10)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print(f"  nginx -t: {out}")
    if err: print(f"  ERR: {err[:200]}")
    
    ssh.exec_command("docker exec ms-nginx nginx -s reload 2>&1", timeout=10)
    time.sleep(2)
    
    # Test ACME
    _, stdout, _ = ssh.exec_command("curl -s -o /dev/null -w 'HTTP %{http_code}' http://localhost/.well-known/acme-challenge/test", timeout=10)
    print(f"  ACME test: {stdout.read().decode().strip()}")
    
    # Step 2: Create SSL Nginx config
    print("\n--- 2/4 创建 SSL 版 Nginx 配置 ---")
    ssl_conf = '''upstream api_backend {
    server api:8000;
}

# ============================================================
# meta-skill.org
# ============================================================
server {
    listen 80;
    server_name meta-skill.org www.meta-skill.org;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl http2;
    server_name meta-skill.org www.meta-skill.org;
    ssl_certificate /etc/letsencrypt/live/meta-skill.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/meta-skill.org/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location = / { return 302 /studio/; }
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
    add_header Strict-Transport-Security "max-age=31536000" always;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;
    gzip_comp_level 5;
}

# ============================================================
# hui-skill.cn
# ============================================================
server {
    listen 80;
    server_name hui-skill.cn www.hui-skill.cn;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl http2;
    server_name hui-skill.cn www.hui-skill.cn;
    ssl_certificate /etc/letsencrypt/live/hui-skill.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hui-skill.cn/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location = / { return 302 /annotate/; }
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
    add_header Strict-Transport-Security "max-age=31536000" always;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;
    gzip_comp_level 5;
}

# ============================================================
# IP 直连
# ============================================================
server {
    listen 80 default_server;
    server_name _;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location = / { return 302 /studio/; }
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
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;
    gzip_comp_level 5;
}
'''
    sftp = ssh.open_sftp()
    with sftp.file(f"{DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill-ssl.conf", 'w') as f:
        f.write(ssl_conf)
    sftp.close()
    print("  meta-skill-ssl.conf 已创建")
    
    # Step 3: Create SSL issue script
    print("\n--- 3/4 创建 SSL 签发 & 启用脚本 ---")
    issue_script = f'''#!/bin/bash
set -e
DEPLOY="{DEPLOY_DIR}"
echo "=== SSL 证书签发 ==="
echo ""

# 签发 meta-skill.org
certbot certonly --webroot -w {DEPLOY}/deploy/certbot/www \\
    -d meta-skill.org -d www.meta-skill.org \\
    --email admin@meta-skill.org --agree-tos --no-eff-email --keep-until-expiring

# 签发 hui-skill.cn
certbot certonly --webroot -w {DEPLOY}/deploy/certbot/www \\
    -d hui-skill.cn -d www.hui-skill.cn \\
    --email admin@hui-skill.cn --agree-tos --no-eff-email --keep-until-expiring

echo ""
echo "证书签发完成！启用 SSL..."
cp {DEPLOY}/deploy/nginx/conf.d/meta-skill.conf {DEPLOY}/deploy/nginx/conf.d/meta-skill-http.conf.bak
cp {DEPLOY}/deploy/nginx/conf.d/meta-skill-ssl.conf {DEPLOY}/deploy/nginx/conf.d/meta-skill.conf

# 更新 docker-compose 证书挂载
sed -i 's|./deploy/certbot/conf:/etc/letsencrypt:ro|/etc/letsencrypt:/etc/letsencrypt:ro|' {DEPLOY}/docker-compose.yml
docker compose -f {DEPLOY}/docker-compose.yml up -d nginx

docker exec ms-nginx nginx -t && docker exec ms-nginx nginx -s reload
echo "=== SSL 已启用 ==="
echo "https://meta-skill.org/"
echo "https://hui-skill.cn/"
'''
    sftp = ssh.open_sftp()
    with sftp.file(f"{DEPLOY_DIR}/ssl-issue.sh", 'w') as f:
        f.write(issue_script)
    ssh.exec_command(f"chmod +x {DEPLOY_DIR}/ssl-issue.sh")
    sftp.close()
    print("  ssl-issue.sh 已创建")
    
    # Step 4: Set up auto-renewal cron
    print("\n--- 4/4 设置自动续期 ---")
    ssh.exec_command(
        '(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook \'docker exec ms-nginx nginx -s reload\'") | crontab -',
        timeout=10
    )
    _, stdout, _ = ssh.exec_command("crontab -l 2>&1", timeout=10)
    print(f"  {stdout.read().decode().strip()}")
    
    # Upload docker-compose.yml
    print("\n--- 上传 docker-compose.yml ---")
    sftp = ssh.open_sftp()
    sftp.put(
        r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\docker-compose.yml",
        f"{DEPLOY_DIR}/docker-compose.yml"
    )
    sftp.close()
    print("  docker-compose.yml 已上传")
    
    # Final verification
    print("\n--- 验证 ---")
    _, stdout, _ = ssh.exec_command("curl -s http://localhost/api/health", timeout=10)
    print(f"  API: {stdout.read().decode().strip()}")
    
    _, stdout, _ = ssh.exec_command("certbot --version 2>&1", timeout=10)
    print(f"  certbot: {stdout.read().decode().strip()}")
    
    _, stdout, _ = ssh.exec_command(f"ls {DEPLOY_DIR}/ssl-issue.sh {DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill-ssl.conf 2>&1", timeout=10)
    print(f"  文件: {stdout.read().decode().strip()}")
    
    print("\n=== SSL 准备完成 ===")
    print("\n待 DNS 配置后运行:")
    print("  ssh root@121.41.215.36")
    print("  bash /opt/meta-skill/ssl-issue.sh")
    
    ssh.close()
    
except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()