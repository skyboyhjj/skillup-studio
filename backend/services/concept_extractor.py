"""
概念提取服务
- 从文本中提取核心概念（DeepSeek API）
- 从微信公众号文章 URL 提取正文内容（httpx + HTML 解析）
- 五行八卦分类（wuxing_engine）
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

import httpx

# 加载 wuxing_engine 模块（兼容本地开发和 Docker 部署）
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_WX_CANDIDATES = [
    _BACKEND_DIR / "wuxing_rules" / "wuxing_engine.py",       # Docker: /app/wuxing_rules/wuxing_engine.py
    Path("/app/wuxing_rules/wuxing_engine.py"),                # Docker fallback
    _BACKEND_DIR.parent / "wuxing_rules" / "wuxing_engine.py", # 本地: backend/../wuxing_rules/wuxing_engine.py
]
_wx_path = None
for _cand in _WX_CANDIDATES:
    if _cand.exists():
        _wx_path = _cand
        break

if _wx_path is None:
    raise FileNotFoundError("找不到 wuxing_engine.py，请检查 wuxing_rules 目录位置")

# wuxing_rules 根目录（用于加载规则文件）
WUXING_DIR = _wx_path.parent  # wuxing_engine.py 所在目录即 wuxing_rules/

_wx_spec = importlib.util.spec_from_file_location("wuxing_engine", str(_wx_path))
_wx_module = importlib.util.module_from_spec(_wx_spec)
sys.modules["wuxing_engine"] = _wx_module
_wx_spec.loader.exec_module(_wx_module)
WuxingEngine = _wx_module.WuxingEngine

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


async def fetch_wechat_article(url: str, timeout_sec: int = 15) -> dict:
    """使用 httpx 获取微信公众号文章正文内容。

    微信公众号文章是服务端渲染的，正文在 #js_content 元素中，
    无需浏览器渲染即可获取文本内容。

    Returns:
        {"title": str, "content": str, "author": str}
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text

            # 提取标题
            title = ""
            title_match = re.search(r'<h1[^>]*class="[^"]*rich_media_title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL)
            if not title_match:
                title_match = re.search(r'id="activity-name"[^>]*>(.*?)</', html, re.DOTALL)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

            # 提取作者
            author = ""
            author_match = re.search(r'id="js_name"[^>]*>(.*?)</', html, re.DOTALL)
            if author_match:
                author = re.sub(r'<[^>]+>', '', author_match.group(1)).strip()

            # 提取正文内容
            content = ""
            content_match = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<script', html, re.DOTALL)
            if not content_match:
                # 尝试更宽松的匹配
                content_match = re.search(r'id="js_content"[^>]*>([\s\S]*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
            if content_match:
                raw = content_match.group(1)
                # 去除 HTML 标签
                content = re.sub(r'<[^>]+>', '', raw)
                # 清理空白
                content = re.sub(r'\n\s*\n', '\n\n', content)
                content = re.sub(r'&nbsp;', ' ', content)
                content = re.sub(r'&amp;', '&', content)
                content = re.sub(r'&lt;', '<', content)
                content = re.sub(r'&gt;', '>', content)
                content = re.sub(r'&quot;', '"', content)
                content = content.strip()

            if not content:
                return {"error": "无法提取文章正文内容，请确认链接是否正确"}

            return {
                "title": title.strip(),
                "content": content.strip(),
                "author": author.strip(),
            }

    except httpx.TimeoutException:
        return {"error": "获取文章超时，请检查网络或稍后重试"}
    except httpx.HTTPStatusError as e:
        return {"error": f"获取文章失败: HTTP {e.response.status_code}"}
    except Exception as e:
        return {"error": f"获取文章失败: {str(e)}"}


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

    user_prompt = "请分析以下文本，提取核心概念并构建三层概念地图。\n\n"
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