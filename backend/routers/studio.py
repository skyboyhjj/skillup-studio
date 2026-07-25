"""Studio API 路由 — 概念提取与莫比乌斯地图生成"""
import re
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.concept_extractor import (
    fetch_wechat_article,
    extract_concepts_from_text,
    run_wuxing_classification,
)
from services.rate_limiter import check_and_increment, get_remaining, DAILY_LIMIT_URL, DAILY_LIMIT_TEXT

router = APIRouter(prefix="/api/studio", tags=["studio"])


class ExtractRequest(BaseModel):
    text: str | None = Field(None, description="直接输入的文本内容")
    url: str | None = Field(None, description="微信公众号文章 URL")
    title: str = Field("", description="可选标题")


class ExtractResponse(BaseModel):
    success: bool
    data: dict | None = None
    source: dict | None = None  # 文章来源信息
    error: str | None = None
    remaining_url: int | None = None  # 今日剩余 URL 提取次数
    remaining_text: int | None = None  # 今日剩余文字提取次数


class QuotaResponse(BaseModel):
    remaining_url: int
    remaining_text: int
    limit_url: int
    limit_text: int


def clean_wechat_url(url: str) -> str:
    """清理微信公众号 URL，移除追踪参数和 scene 参数"""
    try:
        parsed = urlparse(url)
        # 移除 scene 参数（微信分享追踪参数）
        query_parts = parsed.query.split('&')
        cleaned_parts = [p for p in query_parts if not p.startswith('scene=')]
        cleaned_query = '&'.join(cleaned_parts)
        # 重建 URL
        cleaned = parsed._replace(query=cleaned_query)
        return cleaned.geturl()
    except Exception:
        return url


def is_wechat_url(url: str) -> bool:
    """检查是否为微信公众号文章链接"""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and parsed.hostname == "mp.weixin.qq.com"
    except Exception:
        return False


@router.post("/extract", response_model=ExtractResponse)
async def extract_concepts(req: ExtractRequest, request: Request):
    """从文字或微信公众号文章提取概念，返回 rings 结构数据。

    - 如果提供 url：先获取文章正文，再提取概念
    - 如果提供 text：直接对文本提取概念
    - 两者都提供时，优先使用 url
    - 每日限额：URL 提取 5 次，文字提取 5 次（按终端 IP）
    """
    # 参数校验
    if not req.text and not req.url:
        raise HTTPException(status_code=400, detail="请提供 text 或 url 参数")

    # 确定提取类型并检查限额
    if req.url:
        extract_type = "url"
    else:
        extract_type = "text"

    allowed, used, limit = await check_and_increment(request, extract_type)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"今日{extract_type == 'url' and 'URL' or '文字'}提取次数已用完（{limit}/{limit}），请明天再试",
        )

    # 查询剩余次数
    remaining_url = await get_remaining(request, "url")
    remaining_text = await get_remaining(request, "text")

    source_info = {}
    text_to_analyze = ""
    article_title = req.title

    # 如果是 URL，先获取文章内容
    if req.url:
        if not is_wechat_url(req.url):
            raise HTTPException(
                status_code=400,
                detail="仅支持微信公众号文章链接 (mp.weixin.qq.com)",
            )

        # 清理 URL（移除 scene 等追踪参数）
        cleaned_url = clean_wechat_url(req.url)

        article = await fetch_wechat_article(cleaned_url)
        if "error" in article:
            raise HTTPException(status_code=500, detail=article["error"])

        text_to_analyze = article.get("content", "")
        if not text_to_analyze:
            raise HTTPException(status_code=400, detail="无法获取文章正文内容")

        article_title = article_title or article.get("title", "")
        source_info = {
            "type": "wechat",
            "url": req.url,
            "title": article.get("title", ""),
            "author": article.get("author", ""),
        }

    # 如果是直接文本输入
    elif req.text:
        text_to_analyze = req.text.strip()
        if len(text_to_analyze) < 50:
            raise HTTPException(
                status_code=400,
                detail="文本内容太短，请至少输入 50 字",
            )
        source_info = {"type": "text", "length": len(text_to_analyze)}

    # 调用 DeepSeek 提取概念
    result = await extract_concepts_from_text(
        text=text_to_analyze,
        title=article_title,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "概念提取失败"))

    data = result["data"]

    # 用五行引擎做二次分类
    domain = data.get("domain", "default")
    data = run_wuxing_classification(data, domain=domain)

    # 确保 emptiness 配置
    if "emptiness" not in data:
        data["emptiness"] = {
            "sunyata": True,
            "mirror": True,
            "breath": True,
            "wane": True,
            "ascend": True,
            "mirrorRadius": 120,
            "breathPeriod": 10000,
            "breathAmplitude": 15,
            "fadeTarget": 0.15,
            "ascendRatio": 0.2,
        }

    return ExtractResponse(
        success=True,
        data=data,
        source=source_info,
        remaining_url=remaining_url,
        remaining_text=remaining_text,
    )


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(request: Request):
    """查询当前终端今日剩余提取次数"""
    remaining_url = await get_remaining(request, "url")
    remaining_text = await get_remaining(request, "text")
    return QuotaResponse(
        remaining_url=remaining_url,
        remaining_text=remaining_text,
        limit_url=DAILY_LIMIT_URL,
        limit_text=DAILY_LIMIT_TEXT,
    )