"""Meta-Skill.org FastAPI 入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS, LOG_LEVEL
from models.database import init_db
from middleware.domain_guard import DomainGuardMiddleware
from routers import auth, rules, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库表
    await init_db()
    yield


app = FastAPI(
    title="Meta-Skill.org API",
    version="0.1.0",
    description="五行八卦规则引擎 API",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 域名权限守卫（Nginx 通过 X-Domain-Role header 传递域名角色）
app.add_middleware(DomainGuardMiddleware)

# 路由注册
app.include_router(auth.router)
app.include_router(rules.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {"name": "Meta-Skill.org API", "version": "0.1.0", "status": "running"}