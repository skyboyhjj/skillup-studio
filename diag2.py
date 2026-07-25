import paramiko

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=15, banner_timeout=10)
    print("connected")
    
    cmds = [
        "docker exec ms-nginx cat /var/log/nginx/error.log 2>&1 | tail -10",
        "curl -s -o /dev/null -w 'HTTP:%{http_code}\n' http://localhost/",
        "curl -s http://localhost/api/health",
        "docker exec ms-nginx nginx -t 2>&1",
        "docker exec ms-nginx cat /etc/nginx/conf.d/meta-skill.conf 2>&1",
        "docker exec ms-nginx wget -q -O - http://api:8000/api/health 2>&1",
    ]
    for cmd in cmds:
        print(f"\n--- {cmd[:80]} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(out)
        if err:
            print(f"ERR: {err[:300]}")
        
except Exception as e:
    print(f"FAIL: {e}")
finally:
    ssh.close()