# -*- coding: utf-8 -*-
"""
Verified Tasks Bridge Server

将前端 human-reviewed 确认状态持久化到后端 JSON 文件，
实现 localStorage → 后端 JSON 的桥接，使 OKF 导出可捕获人工复核元数据。

用法:
    python verified_server.py                  # 默认端口 8080
    python verified_server.py --port 9090      # 自定义端口

端点:
    GET  /api/verified             → 返回 verified_tasks.json 内容
    POST /api/verify               → 添加确认 {month, source}
    POST /api/unverify             → 移除确认 {month, source}
    GET  /*                        → 静态文件服务（hui-skill-product-matrix/）
"""

import argparse
import json
import os
import sys
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

# 路径配置
SERVER_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SERVER_DIR.parent.resolve()
OUTPUT_DIR = REPO_ROOT / "wuxing_flowengine" / "output"
VERIFIED_FILE = OUTPUT_DIR / "verified_tasks.json"

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_verified() -> dict:
    """加载已验证任务记录"""
    if VERIFIED_FILE.exists():
        try:
            return json.loads(VERIFIED_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_verified(data: dict):
    """保存已验证任务记录"""
    VERIFIED_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


class VerifiedHandler(SimpleHTTPRequestHandler):
    """扩展 SimpleHTTPRequestHandler，增加 API 端点"""

    def __init__(self, *args, **kwargs):
        # 从 SERVER_DIR 提供静态文件
        super().__init__(*args, directory=str(SERVER_DIR), **kwargs)

    def _send_json(self, data: dict, status: int = 200):
        """发送 JSON 响应"""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        """读取 POST 请求体"""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8"))

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)

        if parsed.path == "/api/verified":
            data = load_verified()
            self._send_json(data)
            return

        # 默认：静态文件服务
        try:
            super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            # 浏览器刷新/导航时正常的中止，静默忽略
            pass

    def do_POST(self):
        """处理 POST 请求"""
        parsed = urlparse(self.path)

        if parsed.path == "/api/verify":
            try:
                body = self._read_body()
                month = body.get("month", "")
                source = body.get("source", "")
                if not month or not source:
                    self._send_json({"error": "missing month or source"}, 400)
                    return

                verified = load_verified()
                key = f"{month}|{source}"
                verified[key] = {
                    "by": "human:user",
                    "at": datetime.now().isoformat()
                }
                save_verified(verified)
                self._send_json({"ok": True, "key": key, "verified": verified[key]})
                print(f"  ✓ verified: {key}")
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        if parsed.path == "/api/unverify":
            try:
                body = self._read_body()
                month = body.get("month", "")
                source = body.get("source", "")
                if not month or not source:
                    self._send_json({"error": "missing month or source"}, 400)
                    return

                verified = load_verified()
                key = f"{month}|{source}"
                if key in verified:
                    del verified[key]
                    save_verified(verified)
                    print(f"  ✗ unverified: {key}")
                self._send_json({"ok": True, "key": key})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        # 未匹配的 POST 路径
        self._send_json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        """精简日志输出"""
        if "/api/" in str(args[0]):
            # API 请求：简化日志
            print(f"  [{self.log_date_time_string()}] {args[0]}")
        else:
            # 静态文件：仅记录非 200
            if not (hasattr(args, '__getitem__') and len(args) > 1 and '200' in str(args[1])):
                super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(
        description="Verified Tasks Bridge Server — 前端确认状态持久化桥接"
    )
    parser.add_argument("--port", type=int, default=8080,
                        help="服务端口（默认 8080）")
    args = parser.parse_args()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), VerifiedHandler)

    print(f"Verified Bridge Server")
    print(f"  静态文件: {SERVER_DIR}")
    print(f"  验证数据: {VERIFIED_FILE}")
    print(f"  端口: {args.port}")
    print(f"  端点: GET/POST /api/verified, /api/verify, /api/unverify")
    print(f"  启动: http://localhost:{args.port}/pages/tracker.html")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.server_close()


if __name__ == "__main__":
    main()