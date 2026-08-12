#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mirror Bridge Server — 前端镜鉴入口桥接服务器

将前端 [MIRROR:EVENT] 请求桥接到本地 Python 脚本（S3 生成/B-1 填证/B-2 入池/S4 检索），
沿用 verified_server.py 的桥接模式（SimpleHTTPRequestHandler + JSON API + 静态文件服务）。

用法:
    python mirror_server.py                  # 默认端口 8081
    python mirror_server.py --port 9090      # 自定义端口

端点:
    GET  /api/mirror/health       → 心跳检测（前端模式检测）
    POST /api/mirror/event        → 事件→镜鉴反馈（预览，不落盘）
    POST /api/mirror/card         → 生成 TizhengCard（draft，落盘）
    POST /api/mirror/complete     → 填证三问 → completed（字段映射：practice→done, reflection→cognition_shift）
    POST /api/mirror/pool         → 三道护栏入池（两段式：预览 → 确认）
    GET  /api/mirror/retrieve     → S4 检索（透传 retrieve_crystals.py --json）
    GET  /api/mirror/cards        → 卡片列表（draft/completed）
    GET  /*                        → 静态文件服务（hui-skill-product-matrix/）
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# 路径配置
SERVER_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = SERVER_DIR  # mirror_server.py 所在目录即 scripts/
REPO_ROOT = SERVER_DIR.parent.parent  # scripts → wuxing_flowengine → repo root
STATIC_DIR = REPO_ROOT / "hui-skill-product-matrix"
OUTPUT_DIR = REPO_ROOT / "wuxing_flowengine" / "output"
DB_PATH = REPO_ROOT / "wuxing_flowengine" / "data" / "daojing_database_v2.json"

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 将 scripts 目录加入 sys.path，以便直接 import 本地模块
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def run_script(script_name: str, args: list, timeout: int = 30) -> dict:
    """运行本地 Python 脚本并返回 JSON 结果"""
    script_path = SCRIPTS_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(REPO_ROOT), encoding="utf-8"
        )
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr.strip() or "脚本执行失败",
                    "exit_code": result.returncode}
        return {"ok": True, "output": result.stdout.strip()}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"脚本执行超时（{timeout}s）"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mirror_event(event: str, scores: dict) -> dict:
    """事件→镜鉴反馈（内联逻辑，不落盘）"""
    try:
        from build_tizheng_card import load_db, find_mirror_entry, find_weak_wuxing_chapters
        from contracts import DIMENSION_WUXING, DIMENSION_KEYS, DIMENSION_CN

        db = load_db(DB_PATH)

        # 1. 四维评分 → 最低维度
        # 前端传入中文键名，兼容短键 fallback
        keys = ["时位轴", "宇位轴", "识位轴", "缘位轴"]
        dim_scores = {}
        for dim in keys:
            short_key = DIMENSION_KEYS[dim]
            dim_scores[dim] = scores.get(dim, scores.get(short_key, 5))

        lowest_dim = min(keys, key=lambda d: dim_scores[d])
        weak_wx = DIMENSION_WUXING[lowest_dim]
        p_level = "低" if dim_scores[lowest_dim] < 5 else "高"

        # 2. 镜鉴匹配
        matched = None
        for num in range(1, 82):
            dims = db.get(str(num), {}).get("dimensions", {}).get(lowest_dim, {}).get(p_level, {})
            if any(t and t in event for t in dims.get("triggers", [])):
                matched = find_mirror_entry(db, num, lowest_dim, p_level, event)
                break
        if not matched:
            matched = find_mirror_entry(db, 1, lowest_dim, p_level, event)

        # 3. 推荐经典
        rec_chapters, n_wx = find_weak_wuxing_chapters(db, weak_wx)

        return {
            "ok": True,
            "lowest_dimension": lowest_dim,
            "weak_wuxing": weak_wx,
            "p_level": p_level,
            "mirror": {
                "chapter": matched["chapter"] if matched else 1,
                "title": db.get(str(matched["chapter"]), {}).get("chapter_title", "") if matched else "",
                "dimension": lowest_dim,
                "triggers": matched.get("trigger_hit", []) if matched else [],
                "insight_desc": matched.get("insight_desc", "") if matched else "",
                "action_desc": matched.get("action_desc", "") if matched else "",
                "reflection": matched.get("reflection", "") if matched else "",
            },
            "recommendations": rec_chapters,
            "weak_chapter_count": n_wx,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def scan_tizheng_cards(status_filter: str = None) -> list:
    """扫描 tizheng/ 目录下的卡片"""
    tizheng_dir = OUTPUT_DIR / "crystals" / "tizheng"
    if not tizheng_dir.exists():
        return []
    cards = []
    for f in sorted(tizheng_dir.glob("*.md"), reverse=True):
        try:
            text = f.read_text(encoding="utf-8")
            # 简单解析 frontmatter
            title = ""
            status = "unknown"
            for line in text.splitlines():
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip()
                elif line.startswith("status:"):
                    status = line.split(":", 1)[1].strip()
                if title and status != "unknown":
                    break
            if status_filter and status != status_filter:
                continue
            cards.append({
                "file": f.name,
                "path": str(f.relative_to(REPO_ROOT)),
                "title": title or f.stem,
                "status": status,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
        except Exception:
            continue
    return cards


class MirrorHandler(SimpleHTTPRequestHandler):
    """扩展 SimpleHTTPRequestHandler，增加 /api/mirror/* 端点"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        # /api/mirror/health
        if parsed.path == "/api/mirror/health":
            self._send_json({"ok": True, "mode": "mirror", "version": "1.0"})
            return

        # /api/mirror/retrieve
        if parsed.path == "/api/mirror/retrieve":
            qs = parse_qs(parsed.query)
            args = ["--json"]
            if "bu" in qs:
                args.extend(["--bu", qs["bu"][0]])
            if "wuxing" in qs:
                args.extend(["--wuxing", qs["wuxing"][0]])
            if "kw" in qs:
                args.extend(["--kw", qs["kw"][0]])
            if "status" in qs:
                args.extend(["--status", qs["status"][0]])
            if "type" in qs:
                args.extend(["--type", qs["type"][0]])
            result = run_script("retrieve_crystals.py", args)
            if result["ok"]:
                try:
                    data = json.loads(result["output"])
                    self._send_json({"ok": True, "results": data})
                except json.JSONDecodeError:
                    self._send_json({"ok": True, "output": result["output"]})
            else:
                self._send_json(result, 500)
            return

        # /api/mirror/cards
        if parsed.path == "/api/mirror/cards":
            qs = parse_qs(parsed.query)
            status_filter = qs.get("status", [None])[0]
            cards = scan_tizheng_cards(status_filter)
            self._send_json({"ok": True, "cards": cards})
            return

        # 静态文件
        try:
            super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def do_POST(self):
        parsed = urlparse(self.path)

        # /api/mirror/event
        if parsed.path == "/api/mirror/event":
            try:
                body = self._read_body()
                event = body.get("event", "")
                scores = body.get("scores", {})
                if not event:
                    self._send_json({"ok": False, "error": "missing event"}, 400)
                    return
                result = mirror_event(event, scores)
                self._send_json(result, 200 if result.get("ok") else 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        # /api/mirror/card
        if parsed.path == "/api/mirror/card":
            try:
                body = self._read_body()
                event = body.get("event", "")
                scores = body.get("scores", {})
                user = body.get("user", "hjj")
                if not event:
                    self._send_json({"ok": False, "error": "missing event"}, 400)
                    return

                # 构建 scores 参数（兼容中文键名+短键 fallback）
                def _score(key_cn, key_short):
                    return scores.get(key_cn, scores.get(key_short, 5))
                score_str = f"{_score('时位轴','shi')},{_score('宇位轴','yu')},{_score('识位轴','identify')},{_score('缘位轴','yuan')}"
                args = [
                    "--event", event,
                    "--scores", score_str,
                    "--user", user,
                    "--db", str(DB_PATH),
                    "--out", str(OUTPUT_DIR / "crystals" / "tizheng"),
                ]
                result = run_script("build_tizheng_card.py", args)
                if result["ok"]:
                    output = result["output"]
                    # 从输出中提取文件路径
                    card_path = ""
                    for line in output.splitlines():
                        if "[输出]" in line:
                            card_path = line.split("]", 1)[1].strip()
                            break
                    self._send_json({
                        "ok": True,
                        "card_path": card_path,
                        "output": output,
                    })
                else:
                    self._send_json(result, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        # /api/mirror/complete
        if parsed.path == "/api/mirror/complete":
            try:
                body = self._read_body()
                card_path = body.get("card_path", "")
                evidence = body.get("evidence", {})

                if not card_path:
                    self._send_json({"ok": False, "error": "missing card_path"}, 400)
                    return

                # 字段映射：practice→done, experience→experience, reflection→cognition_shift
                done = evidence.get("practice", "")
                experience = evidence.get("experience", "")
                cognition = evidence.get("reflection", "")

                args = [
                    "--card", card_path,
                    "--done", done,
                    "--experience", experience,
                    "--cognition", cognition,
                ]
                result = run_script("complete_tizheng.py", args)
                if result["ok"]:
                    self._send_json({
                        "ok": True,
                        "card_path": card_path,
                        "status": "completed",
                    })
                else:
                    # 422 自检失败
                    error_msg = result.get("error", "")
                    problems = [p.strip() for p in error_msg.split("\n  - ") if p.strip()]
                    # 过滤掉前缀
                    problems = [p for p in problems if not p.startswith("自检未通过")]
                    self._send_json({
                        "ok": False,
                        "error": "自检未通过",
                        "problems": problems,
                    }, 422)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        # /api/mirror/pool
        if parsed.path == "/api/mirror/pool":
            try:
                body = self._read_body()
                card_path = body.get("card_path", "")
                confirm = body.get("confirm", False)

                if not card_path:
                    self._send_json({"ok": False, "error": "missing card_path"}, 400)
                    return

                args = [
                    "--card", card_path,
                    "--db", str(DB_PATH),
                ]
                if confirm:
                    args.extend(["--confirm", "yes"])
                else:
                    args.extend(["--confirm", "no"])

                result = run_script("pool_tizheng.py", args)
                if result["ok"]:
                    output = result["output"]
                    # 提取 wisdom_id
                    wisdom_id = ""
                    chapter = ""
                    for line in output.splitlines():
                        if "[入池]" in line:
                            wisdom_id = line.split("]", 1)[1].strip().split(" → ")[0]
                        if "chapter=" in line:
                            chapter = line.split("chapter=")[1].split()[0] if " " in line.split("chapter=")[1] else line.split("chapter=")[1]
                    self._send_json({
                        "ok": True,
                        "wisdom_id": wisdom_id,
                        "chapter": chapter,
                        "verified": "human:anonymous",
                        "sample_size": 1,
                        "anonymization": "best-effort",
                    })
                elif not confirm:
                    # 首次无 confirm：返回预览
                    error_msg = result.get("error", "")
                    if "护栏3" in error_msg or "需用户确认" in error_msg:
                        self._send_json({
                            "ok": False,
                            "stage": "await_confirm",
                            "preview": error_msg,
                            "scan_boundary": "匿名化：尽力而为（模式扫描）。已扫描：姓名/手机/邮箱/身份证/公司名/地点；未扫描：上下文推断性识别",
                        })
                    else:
                        self._send_json({"ok": False, "error": error_msg}, 422)
                else:
                    self._send_json({"ok": False, "error": result.get("error", "")}, 422)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        # 未匹配的 POST
        self._send_json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        if "/api/" in str(args[0]):
            print(f"  [{self.log_date_time_string()}] {args[0]}")
        else:
            if not (hasattr(args, '__getitem__') and len(args) > 1 and '200' in str(args[1])):
                super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description="Mirror Bridge Server — 前端镜鉴入口桥接")
    parser.add_argument("--port", type=int, default=8081,
                        help="服务端口（默认 8081，避免与 verified_server 8080 冲突）")
    args = parser.parse_args()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), MirrorHandler)

    print(f"Mirror Bridge Server")
    print(f"  静态文件: {STATIC_DIR}")
    print(f"  数据库: {DB_PATH}")
    print(f"  端口: {args.port}")
    print(f"  端点:")
    print(f"    GET  /api/mirror/health")
    print(f"    POST /api/mirror/event")
    print(f"    POST /api/mirror/card")
    print(f"    POST /api/mirror/complete")
    print(f"    POST /api/mirror/pool")
    print(f"    GET  /api/mirror/retrieve")
    print(f"    GET  /api/mirror/cards")
    print(f"  启动: http://localhost:{args.port}/pages/tracker.html")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.server_close()


if __name__ == "__main__":
    main()