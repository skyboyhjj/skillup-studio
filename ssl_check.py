import paramiko, sys, time

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"
DEPLOY_DIR = "/opt/meta-skill"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=15, banner_timeout=10)
    print("connected")
    
    for cmd in [
        # Check certbot
        "which certbot 2>&1 || echo 'certbot not installed'",
        # Check if already installed
        "snap list certbot 2>&1; apt list --installed 2>/dev/null | grep certbot",
        # Check certbot webroot dirs
        f"ls -la {DEPLOY_DIR}/deploy/certbot/ 2>&1",
        # Check existing certs
        "ls -la /etc/letsencrypt/live/ 2>&1",
        # Check OS
        "cat /etc/os-release | head -3",
        # Check if port 80 is accessible from outside
        "curl -s http://121.41.215.36/api/health",
    ]:
        print(f"\n--- {cmd[:80]} ---")
        _, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out: print(out)
        if err: print(f"ERR: {err[:200]}")
    
    ssh.close()
except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()