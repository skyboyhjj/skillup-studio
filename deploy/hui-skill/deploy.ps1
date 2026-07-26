# hui-skill.cn 部署脚本 (PowerShell)
# 用途: 将 frontend/studio/ 同步到 121.41.215.36 服务器
# 前置: 已配置 SSH 密钥 (见下方密钥配置说明)

param(
    [switch]$nginx,      # 仅上传 Nginx 配置
    [switch]$full,       # 完整部署: 前端 + Nginx 配置
    [string]$user = "root",
    [string]$host = "121.41.215.36"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path "$scriptDir\..\.."
$studioDir = "$projectRoot\frontend\studio"
$remotePath = "/var/www/hui-skill"
$sshTarget = "$user@$host"

# ============================================
# SSH 密钥配置说明 (首次部署前执行一次)
# ============================================
# 1. 生成密钥 (如已有可跳过):
#    ssh-keygen -t ed25519 -C "deploy@hui-skill" -f $env:USERPROFILE\.ssh\hui-skill_deploy
#
# 2. 复制公钥到服务器:
#    type $env:USERPROFILE\.ssh\hui-skill_deploy.pub | ssh root@121.41.215.36 "mkdir -p ~/.ssh ; cat >> ~/.ssh/authorized_keys"
#
# 3. 配置 SSH config (可选，简化连接):
#    编辑 $env:USERPROFILE\.ssh\config，添加:
#    Host hui-skill
#        HostName 121.41.215.36
#        User root
#        IdentityFile ~/.ssh/hui-skill_deploy
#
# 4. 测试连接:
#    ssh hui-skill "echo OK"
# ============================================

function Test-SSH {
    $result = ssh -o ConnectTimeout=5 -o BatchMode=yes $sshTarget "echo OK" 2>&1
    return $LASTEXITCODE -eq 0
}

function Deploy-Frontend {
    Write-Host "=== 部署前端到 $sshTarget ===" -ForegroundColor Cyan

    # 确保远程目录存在
    ssh $sshTarget "mkdir -p $remotePath/studio/preset-data"

    # 同步核心文件
    $files = @(
        "index.html",
        "styles.css",
        "build_mobius.js"
    )
    foreach ($f in $files) {
        $local = "$studioDir\$f"
        $remote = "$remotePath/studio/$f"
        if (Test-Path $local) {
            Write-Host "  上传: $f" -ForegroundColor Green
            scp $local "${sshTarget}:${remote}"
        } else {
            Write-Host "  跳过 (不存在): $f" -ForegroundColor Yellow
        }
    }

    # 同步预设数据集
    Write-Host "  同步预设数据集..." -ForegroundColor Green
    scp -r "$studioDir\preset-data\*.json" "${sshTarget}:${remotePath}/studio/preset-data/"

    Write-Host "  前端部署完成!" -ForegroundColor Green
}

function Deploy-Nginx {
    Write-Host "=== 部署 Nginx 配置到 $sshTarget ===" -ForegroundColor Cyan

    $nginxConf = "$scriptDir\nginx-hui-skill.conf"
    if (-not (Test-Path $nginxConf)) {
        Write-Host "  错误: 找不到 nginx-hui-skill.conf" -ForegroundColor Red
        return
    }

    # 上传配置文件
    scp $nginxConf "${sshTarget}:/etc/nginx/sites-available/hui-skill.cn"

    # 创建软链接并重载 Nginx
    ssh $sshTarget @"
if [ ! -L /etc/nginx/sites-enabled/hui-skill.cn ]; then
    ln -s /etc/nginx/sites-available/hui-skill.cn /etc/nginx/sites-enabled/
fi
nginx -t && systemctl reload nginx && echo 'Nginx 配置已生效'
"@

    Write-Host "  Nginx 部署完成!" -ForegroundColor Green
}

# ============================================
# 主流程
# ============================================

if (-not (Test-SSH)) {
    Write-Host "SSH 连接失败! 请先配置密钥 (见脚本顶部注释)" -ForegroundColor Red
    exit 1
}

if ($full) {
    Deploy-Frontend
    Deploy-Nginx
} elseif ($nginx) {
    Deploy-Nginx
} else {
    Deploy-Frontend
}

Write-Host "`n访问 https://hui-skill.cn/studio/ 验证" -ForegroundColor Cyan