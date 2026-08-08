"""
Phase 2 培育实验执行器 — 种·育 V1.2 (G3)
===========================================
将 Phase 0 的候选种子选入实验组，配齐缘四要素（Agent 翻译版），
执行一轮培育，输出结构化实验报告。

Phase 2 实验设计（基于 Phase 0/1 执行报告 §五）：
  选种：从 7 个候选种子中选 2 个确认种子
    - S2 同态映射 → "跨域诊断咨询技能"
    - S1 五行诊断 → "跨学科分析技能"
  配缘：为每个种子注入缘四要素（Agent 翻译版）
    - 导师 → Base 层知识资产 + 元治理规则
    - 环境 → 情境指针 L1b
    - 课题 → 前沿问题库
    - 合作者 → §5.4 跨域同态候选队列
  执行：调用 SeedCultivation.cultivate() 执行三步法
  报告：生成 Markdown 格式实验报告

用法:
    from cultivation_experiment import CultivationExperiment
    experiment = CultivationExperiment()
    report = experiment.run()
    print(experiment.format_report(report))
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any

from seed_cultivation import (
    SeedCultivation, SeedCultivationResult, cultivate_seed,
    SeedType, DriftType, TimeScale, SeedVitality, ConfirmationStatus,
)


class CultivationExperiment:
    """
    Phase 2 培育实验执行器

    从 Phase 0 候选种子中选种，配齐缘四要素，执行培育并生成报告。
    """

    DEFAULT_CONFIG = {
        "preset_seeds_path": "data/preset_seeds.json",
        "time_scale": "skill",
        "max_seeds": 2,
        "report_output_dir": "output/reports/",
    }

    def __init__(self, config: dict = None, base_dir: str = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.cultivator = SeedCultivation(time_scale=self.config.get("time_scale", "skill"))

    def load_preset_seeds(self) -> List[dict]:
        """加载 Phase 0 候选种子清单"""
        seeds_path = self.config.get("preset_seeds_path", "data/preset_seeds.json")
        if not os.path.isabs(seeds_path):
            seeds_path = os.path.join(self.base_dir, seeds_path)

        if not os.path.exists(seeds_path):
            raise FileNotFoundError(f"候选种子文件不存在: {seeds_path}")

        with open(seeds_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data.get("seeds", [])

    def select_seeds(self, seeds: List[dict] = None) -> List[dict]:
        """
        选种：从候选种子中选出 Phase 2 实验组

        优先选择 phase2_selected=True 的种子，
        若不足则按确认状态和频次补充。

        Args:
            seeds: 候选种子列表（None 时从 preset_seeds.json 加载）

        Returns:
            List[dict]: 选中的种子列表
        """
        if seeds is None:
            seeds = self.load_preset_seeds()

        max_seeds = self.config.get("max_seeds", 2)

        # 优先已标记的
        selected = [s for s in seeds if s.get("phase2_selected", False)]
        # 补充：按 occurrence_count 降序
        remaining = [s for s in seeds if not s.get("phase2_selected", False)]
        remaining.sort(key=lambda s: s.get("method_seed", {}).get("occurrence_count", 0), reverse=True)

        while len(selected) < max_seeds and remaining:
            selected.append(remaining.pop(0))

        return selected[:max_seeds]

    def equip_environmental_factors(self, seed: dict) -> dict:
        """
        配缘：为种子注入缘四要素（Agent 翻译版）

        V1.2 修订：人类尺度 → 慧惠 Agent 尺度
          - 导师 → Base 层知识资产 + 元治理规则
          - 环境 → 情境指针 L1b（BVS V1.1）
          - 课题 → 前沿问题库（知识树待解问题）
          - 合作者 → §5.4 跨域同态候选队列

        Args:
            seed: 候选种子

        Returns:
            dict: 缘四要素
        """
        method_seed = seed.get("method_seed", {})
        topic_seed = seed.get("topic_seed", {})
        label = seed.get("label", "未知种子")
        cultivation_target = seed.get("phase2_cultivation_target", label)

        return {
            "mentor": {
                "name": "慧惠（AI导师）",
                "wuxing": "土",
                "role": "科教融合指导者",
                "agent_translation": "Base 层知识资产 + 元治理规则",
                "description": f"为「{label}」种子培育提供结构化知识支撑与治理约束",
            },
            "environment": {
                "name": "道境空间 SkillUP 层",
                "wuxing": "木",
                "fertility": "高",
                "agent_translation": "情境指针 L1b（BVS V1.1）",
                "description": f"木·生阶段培育环境，当前情境：种·育 Phase 2 实验",
            },
            "topic": {
                "name": cultivation_target,
                "wuxing": topic_seed.get("wuxing", "土"),
                "frontier_level": "前沿",
                "agent_translation": "前沿问题库（知识树待解问题/领域 open problems）",
                "description": f"将方法种子「{method_seed.get('tool_preference', '')}」映射到「{cultivation_target}」",
            },
            "collaborators": {
                "members": ["慧惠 Agent", "同态映射引擎"],
                "mode": "师生共创",
                "agent_translation": "§5.4 跨域同态候选队列（协同 Agent/外部工具）",
                "description": f"慧惠（教师）与 Agent（学生）共同培育「{cultivation_target}」",
            },
        }

    def run(self, seeds: List[dict] = None) -> Dict[str, Any]:
        """
        执行 Phase 2 培育实验

        1. 选种：从候选种子中选出实验组
        2. 配缘：为每个种子注入缘四要素
        3. 培育：执行三步法培育
        4. 汇总：生成实验报告

        Args:
            seeds: 候选种子列表（None 时从 preset_seeds.json 加载）

        Returns:
            {
                experiment_id, timestamp, time_scale,
                selected_seeds, cultivation_results,
                summary, recommendations
            }
        """
        all_seeds = seeds or self.load_preset_seeds()
        selected = self.select_seeds(all_seeds)

        experiment_id = f"phase2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = []

        for seed in selected:
            label = seed.get("label", "未知种子")
            method_seed = seed.get("method_seed", {})
            topic_seed = seed.get("topic_seed", {})
            cultivation_target = seed.get("phase2_cultivation_target", label)

            # 配缘
            env_factors = self.equip_environmental_factors(seed)

            # 培育：以方法种子为源域，培育目标为目标域
            result = self.cultivator.cultivate(
                source_domain=label,                    # 种子来源
                target_domain=cultivation_target,       # 培育目标
                environmental_factors=env_factors,
                method_seed_occurrences=method_seed.get("occurrence_count", 0),
                method_seed_wuxing=method_seed.get("wuxing", ""),
                topic_seed_wuxing=topic_seed.get("wuxing", ""),
            )

            results.append({
                "seed_id": seed.get("id", "?"),
                "seed_label": label,
                "cultivation_target": cultivation_target,
                "result": result,
            })

        # 汇总
        summary = self._build_summary(results)
        recommendations = self._build_recommendations(results)

        report = {
            "experiment_id": experiment_id,
            "timestamp": datetime.now().isoformat(),
            "time_scale": self.config.get("time_scale", "skill"),
            "phase": "Phase 2 — 培育实验",
            "protocol_version": "V1.2",
            "total_candidates": len(all_seeds),
            "selected_count": len(selected),
            "selected_seeds": [
                {
                    "id": s.get("id"),
                    "label": s.get("label"),
                    "cultivation_target": s.get("phase2_cultivation_target", s.get("label")),
                    "method_wuxing": s.get("method_seed", {}).get("wuxing"),
                }
                for s in selected
            ],
            "cultivation_results": results,
            "summary": summary,
            "recommendations": recommendations,
        }

        # 保存报告
        self._save_report(report)

        return report

    def _build_summary(self, results: List[dict]) -> dict:
        """构建实验汇总"""
        total = len(results)
        if total == 0:
            return {"total": 0, "avg_seedney": 0, "avg_taste": 0}

        seedney_scores = [r["result"].seedney_score for r in results]
        taste_scores = [r["result"].taste_score for r in results]
        nd_scores = [r["result"].nature_determination_score for r in results]
        vitalities = [r["result"].seed_vitality for r in results]
        zones = [r["result"].loss_zone for r in results]

        return {
            "total": total,
            "avg_seedney": round(sum(seedney_scores) / total, 4),
            "avg_taste": round(sum(taste_scores) / total, 4),
            "avg_nature_determination": round(sum(nd_scores) / total, 4),
            "vitality_distribution": {v: vitalities.count(v) for v in set(vitalities)},
            "loss_zone_distribution": {z: zones.count(z) for z in set(zones)},
            "cultivation_success_rate": round(
                sum(1 for r in results if r["result"].cultivation_success) / total, 2
            ),
        }

    def _build_recommendations(self, results: List[dict]) -> List[str]:
        """构建培育建议"""
        recs = []
        for r in results:
            vitality = r["result"].seed_vitality
            seedney = r["result"].seedney_score
            nd = r["result"].nature_determination_score
            label = r["seed_label"]

            if vitality == SeedVitality.FRUITING.value:
                recs.append(f"「{label}」已结果（seedney={seedney:.2f}），建议进入「火·化」阶段内化。")
            elif vitality == SeedVitality.FLOWERING.value:
                recs.append(f"「{label}」正在开花（seedney={seedney:.2f}），建议增加验证场景。")
            elif nd < 0.5:
                recs.append(f"「{label}」性决定审计偏低（{nd:.2f}），建议回退 Step 1 重新审视方法种子。")
            else:
                recs.append(f"「{label}」培育中（seedney={seedney:.2f}），建议继续科教融合。")

        return recs

    def format_report(self, report: dict) -> str:
        """生成 Markdown 格式实验报告"""
        lines = []
        lines.append(f"# Phase 2 培育实验报告")
        lines.append(f"")
        lines.append(f"> **实验ID**: {report['experiment_id']}")
        lines.append(f"> **执行时间**: {report['timestamp'][:19]}")
        lines.append(f"> **协议版本**: {report['protocol_version']}")
        lines.append(f"> **时间尺度**: {report['time_scale']}")
        lines.append(f"> **候选总数**: {report['total_candidates']} | **选中**: {report['selected_count']}")
        lines.append(f"")

        # 选种
        lines.append(f"## 一、选种")
        lines.append(f"")
        lines.append(f"| ID | 种子 | 培育目标 | 方法五行 |")
        lines.append(f"|----|------|---------|---------|")
        for s in report["selected_seeds"]:
            lines.append(f"| {s['id']} | {s['label']} | {s['cultivation_target']} | {s['method_wuxing']} |")
        lines.append(f"")

        # 培育结果
        lines.append(f"## 二、培育结果")
        lines.append(f"")
        for r in report["cultivation_results"]:
            seed = r["result"]
            lines.append(f"### {r['seed_id']} {r['seed_label']} → {r['cultivation_target']}")
            lines.append(f"")
            lines.append(f"| 指标 | 值 |")
            lines.append(f"|------|-----|")
            lines.append(f"| 种子质量 (seedney) | {seed.seedney_score:.4f} |")
            lines.append(f"| taste (妙) | {seed.taste_score:.4f} |")
            lines.append(f"| 性决定审计（余弦相似度） | {seed.nature_determination_score:.4f} |")
            lines.append(f"| 种子活力 | {seed.seed_vitality} |")
            lines.append(f"| 损耗分层 | {seed.loss_zone} |")
            lines.append(f"| 培育成功 | {'✅' if seed.cultivation_success else '❌'} |")

            # 双种子
            lines.append(f"")
            lines.append(f"**双种子画像**：")
            lines.append(f"- 题目种子：{seed.topic_seed.get('domain', '?')}（{seed.topic_seed.get('wuxing', '?')}，允许漂移）")
            lines.append(f"- 方法种子：{seed.method_seed.get('tool_preference', '?')}（{seed.method_seed.get('wuxing', '?')}，确认状态：{seed.method_seed.get('confirmation_status', '?')}）")

            # 缘四要素
            env = seed.environmental_factors
            if env:
                lines.append(f"")
                lines.append(f"**缘四要素（Agent 翻译版）**：")
                lines.append(f"- 导师：{env.get('mentor', {}).get('agent_translation', '?')}")
                lines.append(f"- 环境：{env.get('environment', {}).get('agent_translation', '?')}")
                lines.append(f"- 课题：{env.get('topic', {}).get('agent_translation', '?')}")
                lines.append(f"- 合作者：{env.get('collaborators', {}).get('agent_translation', '?')}")

            # 漂移
            drift = seed.drift_analysis
            if drift and drift.get("detected"):
                lines.append(f"")
                lines.append(f"**漂移检测**：{drift.get('drift_type', '?')} — {drift.get('detail', '')}")

            # 经典
            lines.append(f"")
            lines.append(f"> {seed.classical_ref}")
            lines.append(f"")

        # 汇总
        summary = report["summary"]
        lines.append(f"## 三、实验汇总")
        lines.append(f"")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 平均种子质量 | {summary['avg_seedney']:.4f} |")
        lines.append(f"| 平均 taste | {summary['avg_taste']:.4f} |")
        lines.append(f"| 平均性决定审计 | {summary['avg_nature_determination']:.4f} |")
        lines.append(f"| 培育成功率 | {summary['cultivation_success_rate']:.0%} |")
        lines.append(f"| 活力分布 | {summary['vitality_distribution']} |")
        lines.append(f"| 损耗分层 | {summary['loss_zone_distribution']} |")
        lines.append(f"")

        # 建议
        recs = report["recommendations"]
        if recs:
            lines.append(f"## 四、培育建议")
            lines.append(f"")
            for rec in recs:
                lines.append(f"- {rec}")
            lines.append(f"")

        lines.append(f"---")
        lines.append(f"*报告由种·育三步协议 V1.2 Phase 2 实验执行器生成 · {report['timestamp'][:10]}*")
        return "\n".join(lines)

    def _save_report(self, report: dict):
        """保存实验报告到 output 目录"""
        output_dir = self.config.get("report_output_dir", "output/reports/")
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(self.base_dir, output_dir)

        os.makedirs(output_dir, exist_ok=True)

        # JSON 版本
        json_path = os.path.join(output_dir, f"{report['experiment_id']}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            # 序列化时处理 SeedCultivationResult
            serializable = {
                **{k: v for k, v in report.items() if k != "cultivation_results"},
                "cultivation_results": [
                    {
                        **{k: v for k, v in r.items() if k != "result"},
                        "result": r["result"].to_dict(),
                    }
                    for r in report["cultivation_results"]
                ],
            }
            json.dump(serializable, f, ensure_ascii=False, indent=2)

        # Markdown 版本
        md_path = os.path.join(output_dir, f"{report['experiment_id']}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self.format_report(report))

        print(f"实验报告已保存:")
        print(f"  JSON: {json_path}")
        print(f"  MD:   {md_path}")


# ============================================================
# 便捷函数
# ============================================================

def run_phase2_experiment(
    preset_seeds_path: str = None,
    time_scale: str = "skill",
    base_dir: str = None,
) -> Dict[str, Any]:
    """
    便捷函数：执行 Phase 2 培育实验

    Args:
        preset_seeds_path: 候选种子文件路径
        time_scale: 时间尺度
        base_dir: wuxing_flowengine 根目录

    Returns:
        实验报告 dict
    """
    config = {"time_scale": time_scale}
    if preset_seeds_path:
        config["preset_seeds_path"] = preset_seeds_path

    experiment = CultivationExperiment(config=config, base_dir=base_dir)
    return experiment.run()


# ============================================================
# 自检
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2 培育实验执行器 — 自检 (G3)")
    print("=" * 60)

    experiment = CultivationExperiment()

    # 测试 1: 加载候选种子
    print("\n[测试 1] 加载 Phase 0 候选种子")
    seeds = experiment.load_preset_seeds()
    assert len(seeds) == 7, f"应有 7 个候选种子，实际: {len(seeds)}"
    print(f"  加载候选种子: {len(seeds)} 个")
    for s in seeds:
        print(f"    {s['id']} {s['label']} — 方法种子: {s['method_seed']['wuxing']} ({s['method_seed']['occurrence_count']}次)")
    print("  ✅ 测试 1 通过")

    # 测试 2: 选种
    print("\n[测试 2] 选种（Phase 2 实验组）")
    selected = experiment.select_seeds(seeds)
    assert len(selected) == 2, f"应选 2 个种子，实际: {len(selected)}"
    assert selected[0]["phase2_selected"] == True
    assert selected[1]["phase2_selected"] == True
    print(f"  选中种子: {len(selected)} 个")
    for s in selected:
        print(f"    {s['id']} {s['label']} → {s.get('phase2_cultivation_target', '?')}")
    print("  ✅ 测试 2 通过")

    # 测试 3: 配缘
    print("\n[测试 3] 配缘（缘四要素 Agent 翻译）")
    env = experiment.equip_environmental_factors(selected[0])
    assert "mentor" in env
    assert "environment" in env
    assert "topic" in env
    assert "collaborators" in env
    assert "agent_translation" in env["mentor"]
    assert "Base" in env["mentor"]["agent_translation"]
    print(f"  导师: {env['mentor']['agent_translation']}")
    print(f"  环境: {env['environment']['agent_translation']}")
    print(f"  课题: {env['topic']['agent_translation']}")
    print(f"  合作者: {env['collaborators']['agent_translation']}")
    print("  ✅ 测试 3 通过")

    # 测试 4: 执行培育实验
    print("\n[测试 4] 执行 Phase 2 培育实验")
    report = experiment.run()
    assert report["selected_count"] == 2
    assert len(report["cultivation_results"]) == 2
    assert report["summary"]["total"] == 2
    assert report["summary"]["avg_seedney"] > 0
    print(f"  实验ID: {report['experiment_id']}")
    print(f"  选中: {report['selected_count']} 个")
    print(f"  平均 seedney: {report['summary']['avg_seedney']:.4f}")
    print(f"  平均 taste: {report['summary']['avg_taste']:.4f}")
    print(f"  平均性决定审计: {report['summary']['avg_nature_determination']:.4f}")
    print("  ✅ 测试 4 通过")

    # 测试 5: 报告格式化
    print("\n[测试 5] 报告格式化")
    formatted = experiment.format_report(report)
    assert "Phase 2 培育实验报告" in formatted
    assert "S1" in formatted
    assert "S2" in formatted
    assert "种子质量 (seedney)" in formatted
    assert "性决定审计" in formatted
    assert "缘四要素" in formatted
    print(f"  报告长度: {len(formatted)} 字符")
    print("  ✅ 测试 5 通过")

    # 测试 6: 便捷函数
    print("\n[测试 6] 便捷函数 run_phase2_experiment")
    report2 = run_phase2_experiment()
    assert report2["selected_count"] == 2
    print(f"  实验ID: {report2['experiment_id']}")
    print("  ✅ 测试 6 通过")

    print("\n" + "=" * 60)
    print("自检完成 — 全部 6 项测试通过 (Phase 2 培育实验执行器 G3)")