#!/usr/bin/env python3
"""
知识树快照采集器：从知识树 SVG 页面提取节点和边数据
通过浏览器自动化 (browser_evaluate) 提取 SVG DOM 数据
"""
import json, os
from datetime import datetime


def build_snapshot_extraction_script():
    """
    返回一段 JavaScript，在浏览器中执行以提取知识树节点和边数据
    这段 JS 脚本被注入到知识树页面，提取所有 SVG 节点和边
    """
    return """
(function() {
    var nodes = [];
    var edges = [];

    // 提取节点
    var nodeEls = document.querySelectorAll('g.node-item');
    nodeEls.forEach(function(el, i) {
        var textEl = el.querySelector('text');
        var name = textEl ? textEl.textContent.trim() : '';
        var transform = el.getAttribute('transform') || '';
        var match = transform.match(/translate\\(([^,]+),\\s*([^)]+)\\)/);
        var x = match ? parseFloat(match[1]) : 0;
        var y = match ? parseFloat(match[2]) : 0;

        // 判断层级
        var classList = el.className.baseVal || el.getAttribute('class') || '';
        var level = 3;
        if (classList.indexOf('level-1') >= 0) level = 1;
        else if (classList.indexOf('level-2') >= 0) level = 2;

        nodes.push({
            id: 'node_' + String(i + 1).padStart(3, '0'),
            name: name,
            level: level,
            position: { x: Math.round(x * 100) / 100, y: Math.round(y * 100) / 100 }
        });
    });

    // 提取边
    var edgeEls = document.querySelectorAll('line.edge, path.edge');
    edgeEls.forEach(function(el) {
        var x1 = parseFloat(el.getAttribute('x1') || 0);
        var y1 = parseFloat(el.getAttribute('y1') || 0);
        var x2 = parseFloat(el.getAttribute('x2') || 0);
        var y2 = parseFloat(el.getAttribute('y2') || 0);
        edges.push({
            x1: Math.round(x1 * 100) / 100,
            y1: Math.round(y1 * 100) / 100,
            x2: Math.round(x2 * 100) / 100,
            y2: Math.round(y2 * 100) / 100
        });
    });

    return JSON.stringify({
        nodes: nodes,
        edges: edges,
        stats: {
            total_nodes: nodes.length,
            level1_count: nodes.filter(function(n) { return n.level === 1; }).length,
            level2_count: nodes.filter(function(n) { return n.level === 2; }).length,
            level3_count: nodes.filter(function(n) { return n.level === 3; }).length,
            edge_count: edges.length
        }
    });
})();
"""


def save_snapshot(snapshot_data, output_dir, date_str=None):
    """
    保存快照到文件

    参数:
        snapshot_data: {nodes: [...], edges: [...], stats: {...}}
        output_dir: 快照保存目录
        date_str: 日期字符串 (如 "2026-08-03")，默认今天

    返回:
        保存的文件路径
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    snapshot = {
        "collect_time": datetime.now().isoformat(),
        "date": date_str,
        "nodes": snapshot_data["nodes"],
        "edges": snapshot_data["edges"],
        "stats": snapshot_data.get("stats", {
            "total_nodes": len(snapshot_data["nodes"]),
            "edge_count": len(snapshot_data["edges"])
        })
    }

    # 保存完整快照
    snapshot_path = os.path.join(output_dir, f"{date_str}_snapshot.json")
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    # 同时保存 nodes 和 edges 分离版本（兼容旧脚本）
    nodes_path = os.path.join(output_dir, f"{date_str}_nodes.json")
    with open(nodes_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_data["nodes"], f, ensure_ascii=False, indent=2)

    edges_path = os.path.join(output_dir, f"{date_str}_edges.json")
    with open(edges_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_data["edges"], f, ensure_ascii=False, indent=2)

    print(f"  快照已保存: {snapshot_path}")
    print(f"    节点: {len(snapshot_data['nodes'])}, 边: {len(snapshot_data['edges'])}")

    return snapshot_path


def get_snapshot_extraction_steps():
    """
    返回浏览器采集的操作步骤描述，供外部编排器调用
    这些步骤由 monthly_pipeline.py 通过 browser MCP 工具执行
    """
    return {
        "description": "知识树快照采集步骤",
        "steps": [
            {
                "name": "navigate",
                "action": "browser_navigate",
                "url": "https://hub.baai.ac.cn/knowledge-tree/graph"
            },
            {
                "name": "remove_dialog",
                "action": "browser_evaluate",
                "script": "document.querySelector('.hub-dialog__wrapper')?.remove(); document.querySelector('.el-dialog__wrapper')?.remove(); 'done'"
            },
            {
                "name": "wait_for_svg",
                "action": "browser_wait_for",
                "wait_ms": 3000
            },
            {
                "name": "extract_snapshot",
                "action": "browser_evaluate",
                "script": build_snapshot_extraction_script()
            }
        ]
    }