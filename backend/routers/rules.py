"""规则库 API 路由"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import RULES_BASE_PATH, VALID_DOMAINS
from models.database import User, RuleLibrary, DSLAuditLog, get_async_session
from middleware.auth import get_current_user, require_user
from services.dsl_executor import dsl_executor

router = APIRouter(prefix="/api/rules", tags=["rules"])


# ===== 请求模型 =====
class DSLCommand(BaseModel):
    command: str
    concept: str | None = None
    element: str | None = None
    weight: float | None = None
    layer: str | None = None
    stage: str | None = None
    action: str | None = None

class DSLBatchRequest(BaseModel):
    commands: list[DSLCommand]

class RuleUpdateRequest(BaseModel):
    rules_json: dict


# ===== 获取规则库 =====
@router.get("/library")
async def get_library(
    domain: str = Query("chinese_medicine", description="领域"),
    user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """获取当前用户的合并规则库。
    未登录：返回系统默认规则库（从 JSON 文件读取）
    已登录：合并 admin → studio → user 三层规则
    """
    if domain not in VALID_DOMAINS:
        raise HTTPException(status_code=400, detail=f"无效领域: {domain}，可选: {VALID_DOMAINS}")

    if user is None:
        return _load_default_rules(domain)

    # 合并规则：admin → studio → user
    merged = _load_default_rules(domain)

    # 查询用户个人规则库
    result = await session.execute(
        select(RuleLibrary)
        .where(
            RuleLibrary.owner_type == "user",
            RuleLibrary.owner_id == user.id,
            RuleLibrary.domain == domain,
        )
        .order_by(RuleLibrary.version.desc())
        .limit(1)
    )
    personal = result.scalar_one_or_none()
    if personal and personal.rules_json:
        merged = _deep_merge(merged, personal.rules_json)

    return merged


def _load_default_rules(domain: str) -> dict:
    """从 JSON 文件加载默认规则库"""
    file_path = RULES_BASE_PATH / "domains" / f"{domain}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"domain": domain, "concepts": [], "metadata": {"version": "1.0"}}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """深度合并：overlay 覆盖 base 同字段"""
    result = {**base}
    for k, v in overlay.items():
        if k == "concepts" and isinstance(v, list) and "concepts" in result:
            # 概念列表去重合并（overlay 优先）
            concept_map = {c.get("name"): c for c in result["concepts"]}
            for c in v:
                concept_map[c.get("name")] = c
            result["concepts"] = list(concept_map.values())
        elif isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ===== 获取指定规则库 =====
@router.get("/library/{library_id}")
async def get_library_by_id(
    library_id: str,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(RuleLibrary).where(RuleLibrary.id == library_id)
    )
    lib = result.scalar_one_or_none()
    if not lib:
        raise HTTPException(status_code=404, detail="规则库不存在")
    return {
        "id": str(lib.id),
        "owner_type": lib.owner_type,
        "domain": lib.domain,
        "version": lib.version,
        "rules_json": lib.rules_json,
        "updated_at": lib.updated_at.isoformat() if lib.updated_at else None,
    }


# ===== 更新规则库（JSON 批量保存）=====
@router.put("/library/{library_id}")
async def update_library(
    library_id: str,
    req: RuleUpdateRequest,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(RuleLibrary).where(RuleLibrary.id == library_id)
    )
    lib = result.scalar_one_or_none()
    if not lib:
        raise HTTPException(status_code=404, detail="规则库不存在")

    if lib.owner_type == "user" and str(lib.owner_id) != str(user.id):
        raise HTTPException(status_code=403, detail="无权修改此规则库")

    lib.rules_json = req.rules_json
    lib.version += 1
    await session.commit()
    return {"message": "规则库已更新", "version": lib.version}


# ===== 执行 DSL 命令 =====
@router.post("/dsl")
async def execute_dsl(
    cmd: DSLCommand,
    domain: str = Query("chinese_medicine"),
    user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """执行单条 DSL 命令"""
    if domain not in VALID_DOMAINS:
        raise HTTPException(status_code=400, detail=f"无效领域: {domain}")

    # 加载当前规则库
    rules = _load_default_rules(domain)
    if user:
        result = await session.execute(
            select(RuleLibrary)
            .where(
                RuleLibrary.owner_type == "user",
                RuleLibrary.owner_id == user.id,
                RuleLibrary.domain == domain,
            )
            .order_by(RuleLibrary.version.desc())
            .limit(1)
        )
        personal = result.scalar_one_or_none()
        if personal and personal.rules_json:
            rules = _deep_merge(rules, personal.rules_json)

    # 执行 DSL
    result = dsl_executor.execute(
        command={
            "command": cmd.command,
            "concept": cmd.concept or "",
            "element": cmd.element or "",
            "weight": cmd.weight or 0.7,
            "layer": cmd.layer or "",
            "stage": cmd.stage or "",
            "action": cmd.action or "add",
        },
        rules_data=rules,
    )

    # 如果用户已登录，持久化规则库 + 审计日志
    if user and result.get("success"):
        # 保存/更新用户规则库
        existing = await session.execute(
            select(RuleLibrary)
            .where(
                RuleLibrary.owner_type == "user",
                RuleLibrary.owner_id == user.id,
                RuleLibrary.domain == domain,
            )
            .order_by(RuleLibrary.version.desc())
            .limit(1)
        )
        lib = existing.scalar_one_or_none()
        if lib:
            lib.rules_json = result["rules"]
            lib.version += 1
        else:
            lib = RuleLibrary(
                owner_type="user",
                owner_id=user.id,
                domain=domain,
                rules_json=result["rules"],
                version=1,
            )
            session.add(lib)

        # 审计日志
        audit = DSLAuditLog(
            user_id=user.id,
            library_id=lib.id,
            command=cmd.command,
            intent={
                "concept": cmd.concept,
                "element": cmd.element,
                "weight": cmd.weight,
                "layer": cmd.layer,
                "stage": cmd.stage,
                "action": cmd.action,
            },
            result=result,
        )
        session.add(audit)
        await session.commit()

    return result


# ===== 批量执行 DSL =====
@router.post("/dsl/batch")
async def execute_dsl_batch(
    req: DSLBatchRequest,
    domain: str = Query("chinese_medicine"),
    user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    results = []
    for cmd in req.commands:
        results.append(await execute_dsl(cmd, domain, user, session))
    return {"results": results}


# ===== 审计日志 =====
@router.get("/audit")
async def get_audit_logs(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_async_session),
    limit: int = Query(50, le=100),
):
    result = await session.execute(
        select(DSLAuditLog)
        .where(DSLAuditLog.user_id == user.id)
        .order_by(DSLAuditLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "command": log.command,
            "intent": log.intent,
            "result": log.result,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ===== 撤销 =====
@router.post("/undo")
async def undo_last(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_async_session),
):
    """撤销最近一次 DSL 操作（通过快照恢复）"""
    result = await session.execute(
        select(DSLAuditLog)
        .where(DSLAuditLog.user_id == user.id)
        .order_by(DSLAuditLog.created_at.desc())
        .limit(1)
    )
    log = result.scalar_one_or_none()
    if not log or not log.snapshot:
        raise HTTPException(status_code=404, detail="没有可撤销的操作")

    # 恢复规则库快照
    lib_result = await session.execute(
        select(RuleLibrary).where(RuleLibrary.id == log.library_id)
    )
    lib = lib_result.scalar_one_or_none()
    if lib:
        lib.rules_json = log.snapshot
        lib.version += 1
        await session.commit()

    return {"message": "已撤销最近操作"}