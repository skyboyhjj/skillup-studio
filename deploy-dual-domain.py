"""双域名架构部署脚本

将以下文件推送到服务器并重建容器：
1. Nginx 双虚拟主机配置
2. 后端域名权限中间件
3. hui-skill.cn 前端（标注工作台）
4. meta-skill.org 前端更新（注册按钮）
5. docker-compose.yml 环境变量更新
"""
import paramiko, sys, os, time, glob

HOST = "121.41.215.36"
PORT = 22
USER = "root"
PASSWORD = "SXWZJ@ali99"
DEPLOY_DIR = "/opt/meta-skill"
LOCAL_BASE = r"C:\Users\hejij\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a59e217b55e181ea97f0df3"

# 需要上传的文件映射 (local_path -> remote_path)
FILES = {
    # Nginx 配置
    f"{LOCAL_BASE}\\deploy\\nginx\\conf.d\\meta-skill.conf": f"{DEPLOY_DIR}/deploy/nginx/conf.d/meta-skill.conf",
    # 后端
    f"{LOCAL_BASE}\\backend\\config.py": f"{DEPLOY_DIR}/backend/config.py",
    f"{LOCAL_BASE}\\backend\\main.py": f"{DEPLOY_DIR}/backend/main.py",
    f"{LOCAL_BASE}\\backend\\middleware\\domain_guard.py": f"{DEPLOY_DIR}/backend/middleware/domain_guard.py",
    # docker-compose
    f"{LOCAL_BASE}\\docker-compose.yml": f"{DEPLOY_DIR}/docker-compose.yml",
    # meta-skill.org 前端
    f"{LOCAL_BASE}\\frontend\\studio\\index.html": f"{DEPLOY_DIR}/frontend/studio/index.html",
    f"{LOCAL_BASE}\\frontend\\studio\\styles.css": f"{DEPLOY_DIR}/frontend/studio/styles.css",
    # hui-skill.cn 前端
    f"{LOCAL_BASE}\\frontend\\annotate\\index.html": f"{DEPLOY_DIR}/frontend/annotate/index.html",
    f"{LOCAL_BASE}\\frontend\\annotate\\login.html": f"{DEPLOY_DIR}/frontend/annotate/login.html",
    f"{LOCAL_BASE}\\frontend\\annotate\\editor.html": f"{DEPLOY_DIR}/frontend/annotate/editor.html",
}

def ssh_exec(ssh, cmd, print_output=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if print_output:
        if out: print(out)
        if err: print(f"  [ERR] {err[:300]}")
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"连接 {HOST}:{PORT}...")
        ssh.connect(HOST, PORT, USER, PASSWORD, timeout=15, banner_timeout=10)
        print("SSH 已连接\n")
        
        # 1. 确保远程目录存在
        print("--- 1/5 创建远程目录 ---")
        ssh_exec(ssh, f"mkdir -p {DEPLOY_DIR}/backend/middleware {DEPLOY_DIR}/frontend/annotate")
        
        # 2. 上传所有文件
        print("\n--- 2/5 上传文件 ---")
        sftp = ssh.open_sftp()
        uploaded = 0
        failed = []
        for local, remote in FILES.items():
            if not os.path.exists(local):
                print(f"  SKIP (不存在): {local}")
                failed.append(local)
                continue
            try:
                # 确保远程目录存在
                remote_dir = os.path.dirname(remote).replace('\\', '/')
                try:
                    sftp.stat(remote_dir)
                except:
                    ssh_exec(ssh, f"mkdir -p {remote_dir}", print_output=False)
                
                sftp.put(local, remote)
                uploaded += 1
                fname = os.path.basename(local)
                print(f"  OK: {fname}")
            except Exception as e:
                print(f"  FAIL: {os.path.basename(local)} — {e}")
                failed.append(local)
        sftp.close()
        print(f"\n  上传完成: {uploaded}/{len(FILES)} 个文件")
        if failed:
            print(f"  失败: {len(failed)} 个")
        
        # 3. 重建 API 容器
        print("\n--- 3/5 重建 API 容器 ---")
        ssh_exec(ssh, f"cd {DEPLOY_DIR} && docker compose build api")
        
        # 4. 重启服务
        print("\n--- 4/5 重启服务 ---")
        ssh_exec(ssh, f"cd {DEPLOY_DIR} && docker compose up -d")
        
        # 5. 等待并验证
        print("\n--- 5/5 验证 ---")
        time.sleep(15)
        
        print("\n容器状态:")
        ssh_exec(ssh, f"cd {DEPLOY_DIR} && docker compose ps")
        
        print("\nAPI 健康检查:")
        ssh_exec(ssh, "curl -s http://localhost/api/health")
        
        print("\nNginx 配置测试:")
        ssh_exec(ssh, "docker exec ms-nginx nginx -t 2>&1")
        
        print("\n测试 meta-skill.org 风格:")
        ssh_exec(ssh, "curl -s -o /dev/null -w 'HTTP %{http_code}' -H 'Host: meta-skill.org' http://localhost/studio/ && echo ''")
        
        print("\n测试 hui-skill.cn 风格:")
        ssh_exec(ssh, "curl -s -o /dev/null -w 'HTTP %{http_code}' -H 'Host: hui-skill.cn' http://localhost/annotate/ && echo ''")
        
        print("\n=== 部署完成 ===")
        print("\n后续步骤:")
        print("  1. DNS: hui-skill.cn A → 121.41.215.36")
        print("  2. DNS: meta-skill.org A → 121.41.215.36")
        print("  3. 阿里云安全组开放 80/443 端口")
        print("  4. 访问 https://meta-skill.org/studio/ 体验演示")
        print("  5. 访问 https://hui-skill.cn/annotate/ 开始标注")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        ssh.close()

if __name__ == "__main__":
    main()