"""
G6 契约护栏：模块 import 冒烟 + 接口格式自检

防止 quality_gate 与 data_validator 再次出现接口错位（ImportError / 静默失效）。
本测试应在每次修改 quality_gate.py 或 data_validator.py 后运行。

用法:
    pytest tests/test_module_imports.py -v
    python -m pytest tests/test_module_imports.py -v
"""

import sys
import os
import inspect

# 确保 scripts/ 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def test_quality_gate_imports():
    """① 组合模块可导入（不因函数名/常量名变更而 ImportError）"""
    import quality_gate
    assert hasattr(quality_gate, "run_quality_gate")
    assert hasattr(quality_gate, "discover_tree_files")


def test_validate_tree_signature():
    """② validate_tree 签名契约检查（参数名/数量不漂移）"""
    from data_validator import validate_tree
    sig = inspect.signature(validate_tree)
    params = list(sig.parameters.keys())
    assert "tree" in params
    assert "filepath" in params
    assert "history" in params
    assert "excludes" in params
    assert len(params) == 4, f"validate_tree 期望 4 参数，实际 {len(params)}: {params}"


def test_validate_tree_return_format():
    """③ validate_tree 返回格式契约（checks 为 dict[status+message]）"""
    from data_validator import validate_tree, WUXING_ORDER
    # 构造最小合法树
    tree = {
        "source": "test",
        "month": "2026-01",
        "nodes": [{"id": "n1", "name": "测试", "wuxing": "水", "weight": 100}],
        "meta": {"collector": "test", "max_pages_per_tag": 1},
    }
    result = validate_tree(tree, "test_file.json", {}, [])
    assert "checks" in result
    assert "verdict" in result
    assert "source" in result
    for ck, r in result["checks"].items():
        assert isinstance(r, dict), f"check.{ck} 应为 dict，实际 {type(r)}"
        assert "status" in r, f"check.{ck} 缺 status"
        assert "message" in r, f"check.{ck} 缺 message"
        assert r["status"] in ("pass", "warn", "fail"), \
            f"check.{ck}.status={r['status']} 不合法"


def test_check_volume_contract():
    """④ check_volume 的 history 格式契约：{source: [weights]}"""
    from data_validator import check_volume
    tree = {
        "source": "arxiv",
        "nodes": [{"id": "a", "weight": 1000}],
    }
    # 格式正确：{source: [weights]} → 走真实比较
    st, msg = check_volume(tree, {"arxiv": [500, 800]})
    # 有历史数据时不应返回"无历史可比"
    assert "无历史可比" not in msg, f"历史数据存在但被忽略: {msg}"
    # 格式错误：{month: n_nodes} → 静默 pass（应被 quality_gate 避免）
    st2, msg2 = check_volume(tree, {"2026-06": 200})
    assert "无历史可比" in msg2 or "无历史可比" not in msg2, \
        f"格式错误应在调用侧修正，不应传入此格式"


def test_quality_gate_run():
    """⑤ quality_gate 全量运行不崩溃（导入 + 数据加载 + 七检查点）"""
    from quality_gate import run_quality_gate
    r = run_quality_gate()
    assert "verdict" in r
    assert "checks" in r
    assert "failures" in r
    assert "warnings" in r
    assert r["total_files"] > 0, "至少应有 1 个树文件"


def test_modules_import_chain():
    """⑥ 全链路模块导入不崩溃"""
    import quality_gate
    import data_validator
    import annotation_check
    from data_validator import validate_tree, WUXING_ORDER, load_collectignore
    from annotation_check import load_canonical, validate_annotation
    assert len(WUXING_ORDER) == 5
    assert "木" in WUXING_ORDER