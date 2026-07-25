import paramiko, socket
socket.setdefaulttimeout(10)

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=10, banner_timeout=8)
    print("connected")
    stdin, stdout, stderr = ssh.exec_command("docker ps --format '{{.Names}} {{.Status}}'", timeout=8)
    print(stdout.read().decode().strip())
except Exception as e:
    print(f"FAIL: {e}")
finally:
    ssh.close()