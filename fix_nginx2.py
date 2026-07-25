import paramiko, time

HOST = "121.41.215.36"
USER = "root"
PASSWORD = "SXWZJ@ali99"
DEPLOY_DIR = "/opt/meta-skill"
LOCAL = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3\deploy\nginx\conf.d\meta-skill.conf"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=15)
    print("connected")
    
    # Upload
    sftp = ssh.open_sftp()
    sftp.put(LOCAL, f"{DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf")
    sftp.close()
    print("nginx config uploaded")
    
    # Test config
    _, stdout, stderr = ssh.exec_command("docker exec ms-nginx nginx -t 2>&1")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    # Reload
    ssh.exec_command("docker exec ms-nginx nginx -s reload")
    time.sleep(2)
    
    # Test
    for cmd in [
        "curl -s -o /dev/null -w 'meta-skill: HTTP %{http_code}\\n' -H 'Host: meta-skill.org' http://localhost/studio/",
        "curl -s -o /dev/null -w 'hui-skill: HTTP %{http_code}\\n' -H 'Host: hui-skill.cn' http://localhost/annotate/",
        "curl -s -o /dev/null -w 'hui-skill-login: HTTP %{http_code}\\n' -H 'Host: hui-skill.cn' http://localhost/annotate/login.html",
        "curl -s -o /dev/null -w 'hui-skill-editor: HTTP %{http_code}\\n' -H 'Host: hui-skill.cn' http://localhost/annotate/editor.html",
        "curl -s -o /dev/null -w 'IP: HTTP %{http_code}\\n' http://localhost/studio/",
        "curl -s http://localhost/api/health",
    ]:
        _, stdout, _ = ssh.exec_command(cmd, timeout=10)
        print(stdout.read().decode().strip())
    
    print("\nDone!")
    
except Exception as e:
    print(f"FAIL: {e}")
finally:
    ssh.close()