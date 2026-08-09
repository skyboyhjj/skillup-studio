# Phase A 交付报告：pipeline_orchestrator.py（四源并行采集调度器）

**日期**: 2026-08-09
**依据**: 《统一数据运营与展示设计》（DS-OPS-2026-001）Phase A
**状态**: ✅ 开发完成 + 单元验证 24/24 + 真实验证通过

---

## 1. 交付物

| 文件 | 说明 |
|------|------|
| `pipeline_orchestrator.py` | 调度器主程序（零依赖，标准库） |
| `verify/mock_collector.py` | mock 采集器（成功/失败/慢速/超时/前 N 次失败场景） |
| `verify/verify_orchestrator.py` | 单元验证（8 用例 24 断言） |
| `verify/workspace/output/runs/*.json` | 验证产生的运行日志（可审计示例） |

---

## 2. 设计规格 → 实现对照

| 设计规格（DS-OPS-2026-001） | 实现 | 验证 |
|------------------------------|------|:----:|
| 四源并行 `ThreadPoolExecutor(4)` | ✅ 用例 1：4 源并行，总耗时 4.4s < 串行和 | ✅ |
| 重试指数退避 3 次（1s/2s/4s） | ✅ 用例 4：fail-first=2 → attempts=3 成功，退避耗时 ≥3s | ✅ |
| 每源硬超时 15 分钟 | ✅ 可配置 `timeout`，用例 5：timeout=2s 触发 ⏱️（超时不重试） | ✅ |
| 源级容错（单源失败不阻断） | ✅ 用例 1：baai failed 时 arxiv/github/hf 正常 | ✅ |
| 幂等（同月输出存在→skip） | ✅ 用例 2：3 源 skip；失败源无输出→重试 | ✅ |
| 状态机 pending→running→success/failed/skipped/timeout | ✅ 全部状态覆盖 | ✅ |
| 运行日志（run_id/trigger/月/源/汇总） | ✅ 用例 1：日志落盘 `output/runs/run_*.json` | ✅ |
| 断点续跑 `--resume`（只重跑 failed） | ✅ 用例 6：resume 后 sources 仅含 baai | ✅ |
| 触发方式：手动/补采/单源/定时 | ✅ `--month`/`--source`/`--dry-run`/cron 可调 | ✅ |
| 空跑检测（exit=0 但输出缺失） | ✅ 用例 8：识别为 failed（防采集器静默空跑） | ✅ |

**额外健壮性**（超出设计规格）:
- 脚本缺失自动禁用源（`baai_scraper.py` 不存在 → baai 禁用 + 警告）——避免 FileNotFoundError 噪声
- `--force` 覆盖幂等
- `--dry-run` 只输出计划不执行

---

## 3. 单元验证（8 用例 24 断言）

```
✅ 用例 1  四源并行 + 源级容错（elapsed=4.4s < 8s 串行和）
✅ 用例 2  幂等跳过（有输出 skip，无输出重试）
✅ 用例 3  --force 强制重跑
✅ 用例 4  指数退避重试（attempts=3）
✅ 用例 5  硬超时（timeout 状态 + 错误信息）
✅ 用例 6  --resume 断点续跑（只重跑 failed 源）
✅ 用例 7  --dry-run 只输出计划
✅ 用例 8  空跑检测（exit=0 无输出 → failed）
```

## 4. 真实验证（生产注册表）

```
$ python pipeline_orchestrator.py --month 2026-07 --dry-run
  ⚠️ [baai] 脚本缺失，已禁用: baai_scraper.py     ← 本地无生产 baai 脚本
  - arxiv       输出已存在(skip) arxiv_ai_collect.py --month 2026-07
  - github      输出将采集     github_collect.py --month 2026-07
  - huggingface 输出将采集     hf_collect.py --month 2026-07
```

- ✅ 生产命令构造正确（`{python} {script} --month YYYY-MM`，与三个采集脚本接口一致）
- ✅ 幂等识别本地已有 `ai_tree_2026-07.json` → skip
- ✅ 本地环境限制如实呈现（baai 禁用），不假装可用

---

## 5. 生产接入

```powershell
# 生产侧（wuxing_flowengine/scripts/ 或 docs/）
python pipeline_orchestrator.py                    # 全源，最近完整月
python pipeline_orchestrator.py --dir ../docs      # 采集脚本在 docs/（arxiv/github/hf）
python pipeline_orchestrator.py --source arxiv --month 2026-08   # 单源补采
python pipeline_orchestrator.py --resume           # 失败源断点续跑
```

**定时调度**（cron，每月 1 日 03:00）:
```
0 3 1 * * cd /path/to/wuxing_flowengine && python pipeline_orchestrator.py >> output/logs/pipeline.log 2>&1
```

**注意**: 生产侧 baai 采集脚本为 `scripts/baai_scraper.py`，与 arxiv/github/hf（docs/）目录不同——若 baai 需与其余三源同一 --dir，建议在 scripts/ 建软链或调整注册表路径。

---

## 6. 已知限制与 Phase B 衔接

| 限制 | 说明 | Phase B 衔接 |
|------|------|--------------|
| 无质量门 | 调度只查"输出存在"，未跑七检查点 | Phase B: 调度链末端接 data_validator 七检查点 + 质量报告 |
| 无版本链 | 树文件尚无 metadata/provenance | Phase B: schema v1.1 + 版本戳 |
| 无监控面板 | 日志可审计但无可视化 | Phase C: dashboard_data.json 打包 + tracker.html 质量区 |

---

## 7. 结论

> **Phase A 完成：调度器实现设计规格 10/10 + 2 项额外健壮性，24/24 断言通过，生产命令对接验证通过。** 四源采集从"串行手动"升级为"一键并行、源级容错、断点续跑、日志可审计"。运营层的"生"已就位——下一步 Phase B（质量门七检查点 + 版本链）让每一份进入诊断的数据都"过门而入"。

*验证可复跑: `python verify/verify_orchestrator.py`*
