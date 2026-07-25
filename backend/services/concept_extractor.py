"""
概念提取服务
- 从文本中提取核心概念（DeepSeek API）
- 从微信公众号文章 URL 提取正文内容（Playwright）
- 五行八卦分类（wuxing_engine）
"""
import json
import re
import sys
import asyncio
from pathlib import Path
from typing import Optional

import httpx

# 添加 wuxing_rules 到路径
WUXING_DIR = Path(__file__).resolve().parent.parent.parent / "wuxing_rules"
if str(WUXING_DIR) not in sys.path:
    sys.path.insert(0, str(WUXING_DIR))

from wuxing_engine import WuxingEngine

# DeepSeek 配置
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

# 系统提示词：概念提取
CONCEPT_EXTRACTION_SYSTEM = """你是一个专业的文本分析专家，擅长从文章中提取核心概念并构建知识图谱。

## 任务
从用户提供的文本中提取 15-25 个核心概念，并将它们组织为三层结构：

1. **基础层**（6-8 个概念）：文章的基础概念、背景知识、核心定义
2. **核心层**（6-8 个概念）：文章的核心论点、关键方法、主要论证
3. **前沿层**（4-6 个概念）：文章的延伸思考、应用场景、未来展望

## 提取规则
- 概念可以是：方法论、框架、理论、技术、工具、人物、策略、应用场景等
- 排除过于宽泛的词汇（如"学习""工作""生活"）
- 每个概念需要 30-80 字的简洁描述
- 每个概念需要推断五行属性（木/火/土/金/水）和八卦属性（☰乾/☱兑/☲离/☳震/☴巽/☵坎/☶艮/☷坤）

## 五行推断参考
- 木：生长、创新、教育、发展、初创、理论萌芽
- 火：爆发、传播、流行、变革、突破、颠覆性
- 土：整合、平台、基础、生态、协调、标准化
- 金：结构化、规范、效率、工具、算法、工程化
- 水：流动、适应、深度、反思、安全、伦理

## 输出格式
严格按以下 JSON 格式输出，不要包含任何其他文字：

```json
{
  "title": "文章标题（从内容中提取，不超过20字）",
  "domain": "领域标识（如 science_technology, chinese_medicine, daojism, confucianism, buddhism, mathematics, western_philosophy 或 general）",
  "rings": [
    {
      "label": "基础层",
      "R": 200,
      "w": 30,
      "yOffset": 120,
      "color": "#3498DB",
      "concepts": [
        {
          "label": "概念名称",
          "desc": "30-80字的简洁描述",
          "wuxing": "木",
          "bagua": "☳震",
          "docs": ["文章标题"]
        }
      ]
    },
    {
      "label": "核心层",
      "R": 150,
      "w": 25,
      "yOffset": 0,
      "color": "#2ECC71",
      "concepts": [...]
    },
    {
      "label": "前沿层",
      "R": 100,
      "w": 20,
      "yOffset": -120,
      "color": "#9B59B6",
      "concepts": [...]
    }
  ]
}
```

## 重要约束
- 每个概念必须有 label, desc, wuxing, bagua, docs 字段
- wuxing 必须是 木/火/土/金/水 之一
- bagua 必须是 ☰乾/☱兑/☲离/☳震/☴巽/☵坎/☶艮/☷坤 之一
- 节点总数在 15-25 之间
- 确保 JSON 格式正确，可直接解析"""


async def fetch_wechat_article(url: str, timeout_sec: int = 30) -> dict:
    """使用 Playwright 获取微信公众号文章正文内容。

    Returns:
        {"title": str, "content": str, "author": str}
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"error": "playwright 未安装，请执行: pip install playwright && python -m playwright install chromium"}

    timeout_ms = timeout_sec * 1000

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )

        try:
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)

            # 等待文章内容加载
            try:
                await page.wait_for_selector("#js_content", timeout=15000)
            except Exception:
                pass

            # 提取文章标题
            title = await page.evaluate("""
                () => {
                    const el = document.querySelector('#activity-name');
                    return el ? el.textContent.trim() : '';
                }
            """) or await page.title()

            # 提取作者
            author = await page.evaluate("""
                () => {
                    const el = document.querySelector('#js_name');
                    return el ? el.textContent.trim() : '';
                }
            """)

            # 提取正文内容
            content = await page.evaluate("""
                () => {
                    const el = document.querySelector('#js_content');
                    if (!el) return '';
                    return el.innerText.trim();
                }
            """)

            return {
                "title": title.strip(),
                "content": content.strip(),
                "author": author.strip(),
            }

        finally:
            await browser.close()


async def extract_concepts_from_text(
    text: str,
    title: str = "",
    deepseek_key: str = "",
    deepseek_url: str = "",
) -> dict:
    """使用 DeepSeek API 从文本中提取概念。

    Args:
        text: 要分析的文本
        title: 文章标题（可选，用于提示）
        deepseek_key: DeepSeek API Key
        deepseek_url: DeepSeek API Base URL

    Returns:
        {"success": bool, "data": {...}, "error": str}
    """
    api_key = deepseek_key or DEEPSEEK_API_KEY
    base_url = deepseek_url or DEEPSEEK_BASE_URL

    if not api_key:
        return {"success": False, "error": "DeepSeek API Key 未配置"}

    user_prompt = f"请分析以下文本，提取核心概念并构建三层概念地图。\n\n"
    if title:
        user_prompt += f"文章标题：{title}\n\n"
    user_prompt += f"文本内容：\n{text[:8000]}"  # 限制长度避免 token 超限

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": CONCEPT_EXTRACTION_SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
            )

            if response.status_code != 200:
                return {"success": False, "error": f"DeepSeek API 错误: {response.status_code} {response.text[:200]}"}

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 提取 JSON（可能被 markdown 代码块包裹）
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_str = content.strip()

            data = json.loads(json_str)

            # 验证基本结构
            if "rings" not in data:
                return {"success": False, "error": "LLM 返回的数据缺少 rings 字段"}

            return {"success": True, "data": data}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON 解析失败: {str(e)}", "raw_response": content}
    except httpx.TimeoutException:
        return {"success": False, "error": "DeepSeek API 请求超时"}
    except Exception as e:
        return {"success": False, "error": f"概念提取失败: {str(e)}"}


def run_wuxing_classification(data: dict, domain: str = "default") -> dict:
    """使用五行引擎对概念进行二次分类，覆盖 LLM 可能不准确的推断。

    Args:
        data: LLM 返回的 rings 数据
        domain: 知识领域

    Returns:
        经过五行引擎分类的数据
    """
    try:
        engine = WuxingEngine(
            rules_path=str(WUXING_DIR / "rules" / "wuxing_bagua_rules.json"),
            domain=domain,
        )

        for ring in data.get("rings", []):
            for concept in ring.get("concepts", []):
                label = concept.get("label", "")
                desc = concept.get("desc", "")

                # 五行推断
                wx = engine.infer_wuxing(label, desc)
                concept["wuxing"] = wx

                # 八卦推断
                bg = engine.infer_bagua(label, desc, wx)
                concept["bagua"] = bg

        return data

    except Exception as e:
        # 如果五行引擎失败，保留 LLM 原始分类
        print(f"五行引擎分类失败，保留原始推断: {e}")
        return data