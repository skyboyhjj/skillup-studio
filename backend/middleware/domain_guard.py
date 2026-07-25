"""域名权限中间件

Nginx 通过 X-Domain-Role header 传递域名角色：
- demo: meta-skill.org — 只读（浏览规则库、运行演示）
- full: hui-skill.cn — 完整读写（注册、标注、修改规则库）

未携带 header 时默认视为 demo 模式。
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

# 需要写权限的 API 路径前缀
WRITE_REQUIRED_PREFIXES = (
    "/api/auth/register",
    "/api/auth/login",
    "/api/rules/dsl/execute",
    "/api/rules/library/update",
    "/api/rules/library/create",
    "/api/rules/library/delete",
    "/api/rules/library/import",
    "/api/rules/library/export",
)

# 写操作需要的方法
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class DomainGuardMiddleware(BaseHTTPMiddleware):
    """基于域名的权限守卫"""

    async def dispatch(self, request: Request, call_next):
        domain_role = request.headers.get("X-Domain-Role", "demo")

        # 检查是否需要写权限
        needs_write = self._needs_write(request)
        if needs_write and domain_role != "full":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="meta-skill.org 仅支持浏览体验，请在 hui-skill.cn 注册后进行数据标注",
            )

        response = await call_next(request)
        return response

    def _needs_write(self, request: Request) -> bool:
        """判断请求是否需要写权限"""
        path = request.url.path
        method = request.method

        # GET / HEAD 始终允许
        if method in ("GET", "HEAD", "OPTIONS"):
            return False

        # 精确匹配写操作路径
        for prefix in WRITE_REQUIRED_PREFIXES:
            if path.startswith(prefix):
                return True

        # 其他 WRITE_METHODS 也检查
        if method in WRITE_METHODS:
            return True

        return False


# 注册/登录路径显式标记（用于前端判断）
LOGIN_REQUIRED_PATHS = (
    "/api/auth/register",
)