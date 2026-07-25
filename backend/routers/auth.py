"""认证 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import User, get_async_session
from middleware.auth import get_current_user, require_user
from services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ===== 请求/响应模型 =====
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    contribution_level: int
    avatar_url: str | None = None


# ===== 注册 =====
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, session: AsyncSession = Depends(get_async_session)):
    # 检查用户名
    result = await session.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱
    result = await session.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        role="registered",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        user={"id": str(user.id), "username": user.username, "email": user.email, "role": user.role}
    )


# ===== 登录 =====
@router.post("/login")
async def login(req: LoginRequest, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        user={"id": str(user.id), "username": user.username, "email": user.email, "role": user.role}
    )


# ===== 获取当前用户 =====
@router.get("/me")
async def me(user: User | None = Depends(get_current_user)):
    if user is None:
        return {"authenticated": False, "user": None}
    return {
        "authenticated": True,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "contribution_level": user.contribution_level,
            "avatar_url": user.avatar_url,
        }
    }


# ===== 更新个人资料 =====
class UpdateProfileRequest(BaseModel):
    avatar_url: str | None = None

@router.put("/profile")
async def update_profile(
    req: UpdateProfileRequest,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_async_session),
):
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url
    await session.commit()
    return {"message": "资料已更新"}