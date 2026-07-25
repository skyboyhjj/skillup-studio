import paramiko

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=15, banner_timeout=10)
    print("connected")
    
    channel = ssh.get_transport().open_session()
    channel.settimeout(20)
    channel.exec_command(
        'echo "==STATUS=="; docker ps --format "{{.Names}} {{.Status}}" 2>&1; '
        'echo "==API_LOG=="; docker logs --tail 20 ms-api 2>&1; '
        'echo "==NGINX_ERR=="; docker exec ms-nginx cat /var/log/nginx/error.log 2>&1 | tail -10; '
        'echo "==TEST=="; curl -s http://localhost/api/health 2>&1; '
        'echo "==NGINX_CONF=="; docker exec ms-nginx cat /etc/nginx/conf.d/meta-skill.conf 2>&1'
    )
    
    out = b""
    while not channel.exit_status_ready():
        if channel.recv_ready():
            out += channel.recv(4096)
        if channel.recv_stderr_ready():
            out += channel.recv_stderr(4096)
    
    # Read any remaining
    while channel.recv_ready():
        out += channel.recv(4096)
    while channel.recv_stderr_ready():
        out += channel.recv_stderr(4096)
    
    print(out.decode(errors='replace'))
    
except Exception as e:
    print(f"FAIL: {e}")
finally:
    ssh.close()