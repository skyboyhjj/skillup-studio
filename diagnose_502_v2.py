"""深度诊断 502：检查容器状态、API 日志、Nginx 日志"""
import paramiko
import sys

HOST = "121.41.215.36"
PORT = 22
USER = "root"
PASSWORD = "SXWZJ@ali99"
DEPLOY_DIR = "/opt/meta-skill"

def ssh_exec(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err:
        print(f"[STDERR] {err}")
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(HOST, PORT, USER, PASSWORD, timeout=30)
        print("=== SSH 连接成功 ===\n")
        
        print("--- 容器状态 ---")
        ssh_exec(ssh, f"cd {DEPLOY_DIR} && docker compose ps")
        
        print("\n--- API 最近日志 (最近 80 行) ---")
        ssh_exec(ssh, "docker logs --tail 80 ms-api 2>&1")
        
        print("\n--- Nginx 错误日志 (最近 30 行) ---")
        ssh_exec(ssh, "docker exec ms-nginx cat /var/log/nginx/error.log 2>&1 | tail -30")
        
        print("\n--- 宿主机直接测试 ---")
        ssh_exec(ssh, "curl -s -o /dev/null -w 'HTTP %{http_code}' http://localhost/ && echo ''")
        ssh_exec(ssh, "curl -s http://localhost/api/health")
        
        print("\n--- Nginx -> API 连通性 ---")
        ssh_exec(ssh, "docker exec ms-nginx wget -q -O - http://api:8000/api/health 2>&1")
        
        print("\n--- 检查 Nginx 配置 ---")
        ssh_exec(ssh, "docker exec ms-nginx cat /etc/nginx/conf.d/meta-skill.conf 2>&1")
        
        print("\n--- 防火墙检查 ---")
        ssh_exec(ssh, "ufw status 2>&1")
        
        print("\n--- 阿里云安全组提示 ---")
        print("请确认阿里云控制台安全组已开放 80 端口")
        
        print("\n=== 完成 ===")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
    finally:
        ssh.close()

if __name__ == "__main__":
    main()