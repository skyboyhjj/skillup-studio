import paramiko, sys, time

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=15, banner_timeout=10)
    print("connected")
    
    for cmd in [
        "docker ps --format '{{.Names}} {{.Status}}'",
        "docker logs --tail 15 ms-api 2>&1",
        "docker exec ms-nginx cat /var/log/nginx/error.log 2>&1 | tail -5",
        "curl -s -o /dev/null -w 'HTTP:%{http_code}\n' http://localhost/",
        "curl -s http://localhost/api/health",
    ]:
        print(f"\n--- {cmd[:60]} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        print(stdout.read().decode().strip())
        err = stderr.read().decode().strip()
        if err:
            print(f"ERR: {err[:200]}")

except Exception as e:
    print(f"FAIL: {e}")
finally:
    ssh.close()