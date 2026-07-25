import paramiko

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=15, banner_timeout=10)
    print("connected")
    for cmd in [
        "docker ps --format '{{.Names}} {{.Image}} {{.Status}}'",
        "ls /opt/meta-skill/frontend/",
        "ls /opt/meta-skill/backend/",
        "cat /opt/meta-skill/.env 2>/dev/null | head -5",
        "df -h / | tail -1",
        "free -m | grep Mem",
        "cat /opt/meta-skill/docker-compose.yml | head -60",
        "dig +short hui-skill.cn 2>/dev/null || nslookup hui-skill.cn 2>/dev/null | grep Address || echo 'DNS not resolved'",
        "dig +short meta-skill.org 2>/dev/null || nslookup meta-skill.org 2>/dev/null | grep Address || echo 'DNS not resolved'",
        "cat /opt/meta-skill/deploy/nginx/conf.d/meta-skill.conf",
        "docker exec ms-db psql -U ms_user -d meta_skill -c '\\dt' 2>&1",
    ]:
        print(f"\n--- {cmd[:80]} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out: print(out)
        if err: print(f"ERR: {err[:300]}")
except Exception as e:
    print(f"FAIL: {e}")
finally:
    ssh.close()