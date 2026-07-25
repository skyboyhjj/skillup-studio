import paramiko, sys
HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=15, banner_timeout=10)
    print("connected")
    for cmd in [
        "iptables -L INPUT -n 2>&1 | head -25",
        "ufw status 2>&1",
        "ss -tlnp 2>&1 | grep -E '80|443'",
        "curl -s http://localhost/api/health",
    ]:
        print(f"\n--- {cmd[:60]} ---")
        _, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        print(stdout.read().decode().strip())
        err = stderr.read().decode().strip()
        if err: print(f"ERR: {err[:200]}")
except Exception as e:
    print(f"FAIL: {e}")
finally:
    ssh.close()