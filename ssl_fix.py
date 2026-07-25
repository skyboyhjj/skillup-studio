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
    
    # Create issue+enable script
    print("--- 创建 SSL 签发脚本 ---")
    script = """#!/bin/bash
set -e
D="/opt/meta-skill"
echo "=== SSL 证书签发 ==="
echo ""

# 签发 meta-skill.org
certbot certonly --webroot -w $D/deploy/certbot/www \\
    -d meta-skill.org -d www.meta-skill.org \\
    --email admin@meta-skill.org --agree-tos --no-eff-email --keep-until-expiring

# 签发 hui-skill.cn
certbot certonly --webroot -w $D/deploy/certbot/www \\
    -d hui-skill.cn -d www.hui-skill.cn \\
    --email admin@hui-skill.cn --agree-tos --no-eff-email --keep-until-expiring

echo ""
echo "证书签发完成！启用 SSL..."

# 备份当前 HTTP 配置
cp $D/deploy/nginx/conf.d/meta-skill.conf $D/deploy/nginx/conf.d/meta-skill-http.conf.bak

# 替换为 SSL 配置
cp $D/deploy/nginx/conf.d/meta-skill-ssl.conf $D/deploy/nginx/conf.d/meta-skill.conf

# 重启 Nginx
docker compose -f $D/docker-compose.yml up -d nginx
sleep 2
docker exec ms-nginx nginx -t && docker exec ms-nginx nginx -s reload

echo ""
echo "=== SSL 已启用 ==="
echo "https://meta-skill.org/"
echo "https://hui-skill.cn/"
"""
    
    sftp = ssh.open_sftp()
    with sftp.file(f"{DEPLOY_DIR}/ssl-issue.sh", 'w') as f:
        f.write(script)
    ssh.exec_command(f"chmod +x {DEPLOY_DIR}/ssl-issue.sh")
    sftp.close()
    print("  ssl-issue.sh 已创建")
    
    # Set up cron for auto-renewal
    print("\n--- 设置自动续期 ---")
    ssh.exec_command(
        '(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook \'docker exec ms-nginx nginx -s reload\' 2>&1 | logger -t certbot-renew") | crontab -',
        timeout=10
    )
    _, stdout, _ = ssh.exec_command("crontab -l 2>&1", timeout=10)
    print(f"  {stdout.read().decode().strip()}")
    
    # Verify ACME path
    print("\n--- 验证 ACME challenge ---")
    _, stdout, _ = ssh.exec_command(
        "curl -s -o /dev/null -w 'HTTP %{http_code}' http://localhost/.well-known/acme-challenge/test && echo ''",
        timeout=10
    )
    print(f"  {stdout.read().decode().strip()}")
    _, stdout, _ = ssh.exec_command(
        "curl -s -o /dev/null -w 'HTTP %{http_code}' -H 'Host: meta-skill.org' http://localhost/.well-known/acme-challenge/test && echo ''",
        timeout=10
    )
    print(f"  meta-skill.org: {stdout.read().decode().strip()}")
    _, stdout, _ = ssh.exec_command(
        "curl -s -o /dev/null -w 'HTTP %{http_code}' -H 'Host: hui-skill.cn' http://localhost/.well-known/acme-challenge/test && echo ''",
        timeout=10
    )
    print(f"  hui-skill.cn: {stdout.read().decode().strip()}")
    
    # Verify files
    print("\n--- 文件清单 ---")
    _, stdout, _ = ssh.exec_command(
        f"ls -la {DEPLOY_DIR}/ssl-issue.sh {DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill-ssl.conf {DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf",
        timeout=10
    )
    print(stdout.read().decode().strip())
    
    print("\n=== SSL 准备完成 ===\n")
    print("待 DNS 配置后，在服务器上运行:")
    print("  ssh root@121.41.215.36")
    print("  bash /opt/meta-skill/ssl-issue.sh")
    print("\n这个脚本会自动完成:")
    print("  1. 签发 meta-skill.org 和 hui-skill.cn 的 Let's Encrypt 证书")
    print("  2. 替换 Nginx 配置为 HTTPS 版本")
    print("  3. 重载 Nginx 启用 SSL")
    print("  4. 已配置每天凌晨 3 点自动续期")
    
    ssh.close()
    
except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()