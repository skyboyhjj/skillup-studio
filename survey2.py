import paramiko, socket, json
socket.setdefaulttimeout(8)

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=8, banner_timeout=6)
    print("connected")
    
    # Collect all info in one session
    for cmd in [
        "docker ps --format '{{.Names}} {{.Status}}'",
        "docker exec ms-nginx cat /etc/nginx/conf.d/meta-skill.conf",
        "ls /opt/meta-skill/frontend/",
        "cat /opt/meta-skill/.env | head -8",
        "cat /opt/meta-skill/deploy/nginx/nginx.conf",
        "docker exec ms-db psql -U ms_user -d meta_skill -c '\\dt' 2>&1",
        "cat /opt/meta-skill/backend/config.py",
    ]:
        print(f"\n=== {cmd[:80]} ===")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=8)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out: print(out)
        if err: print(f"ERR: {err[:300]}")
    
    ssh.close()
except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()