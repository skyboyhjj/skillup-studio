#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mock 采集器（Phase A 单元验证用）——模拟四源采集行为"""
import argparse
import json
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--month", required=True)
p.add_argument("--source", required=True)
p.add_argument("--fail", action="store_true", help="总是失败")
p.add_argument("--delay", type=float, default=0.0, help="模拟耗时")
p.add_argument("--fail-first", type=int, default=0, help="前 N 次失败（用标记文件计数）")
p.add_argument("--empty", action="store_true", help="退出码 0 但不产生输出")
a = p.parse_args()

time.sleep(a.delay)

if a.fail:
    print(f"[mock:{a.source}] 模拟失败 exit=1", file=__import__("sys").stderr)
    raise SystemExit(1)

if a.fail_first > 0:
    mark = Path(f".mock_attempt_{a.source}")
    n = int(mark.read_text()) if mark.exists() else 0
    n += 1
    mark.write_text(str(n))
    if n <= a.fail_first:
        print(f"[mock:{a.source}] 第 {n}/{a.fail_first} 次失败", file=__import__("sys").stderr)
        raise SystemExit(2)

if a.empty:
    print(f"[mock:{a.source}] 空跑 exit=0 无输出")
    raise SystemExit(0)

m = a.month.replace("-", "")
# 生产命名映射（huggingface → hf 前缀，与生产 hf_collect.py 一致）
prefix = {"huggingface": "hf", "arxiv": "arxiv", "github": "github", "baai": "baai"}.get(a.source, a.source)
Path(f"{prefix}_tree_{m}.json").write_text(
    json.dumps({"source": a.source, "month": a.month, "nodes": [],
                "mock": True}), encoding="utf-8")
print(f"[mock:{a.source}] {a.month} 采集完成 → {prefix}_tree_{m}.json")
