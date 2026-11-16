# 最小交接消费者

`minimal_prd_consumer.py` 用于阶段 4 验证交接约定，不是完整 PRD Generator，不随 Requirement Analyst 安装。无模型调用，不需要 API Key。

## 运行

与 Skill 的脚本使用相同 Python 3.10+ 和依赖：`jsonschema[format]==4.26.0`。支持 Linux/Unix 本地工作区。以下命令均在仓库根目录执行；脚本自身不依赖当前目录，也可以使用绝对路径从别处调用。

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tools/minimal_prd_consumer.py \
  --workspace /path/to/requirement-workspace --project example --requirement REQ-2026-001
```

工作区和需求必须先由分析更新器建立；没有结果时只返回交接请求，不创建需求目录。不会读取 `analysis-report.md`。

可选参数：

- `--inspect-only`：校验并比较修订号，不写草稿。`sync_state` 为 `absent`、`current` 或 `pending`，仅当前响应中存在。
- `--expected-revision N`：基于用户实际看到的分析版本生成；冲突先重读，不能盲改数字重试。
- `--insist-stale`：仅在用户明确坚持使用过期分析时使用；不能绕过校验 fail，草稿仍标“基于过期分析”。
- `--require-section requirements.acceptance_criteria`：模板明确要求的规范条目集合；可重复，路径可选值见 `--help`。无 active 条目则返回缺口请求；不做自然语言业务充分性判断。
- `--related-analysis /path/to/analysis-result.json`：显式关联结果，可重复；读取其同目录的 `source-manifest.json`，不隐式搜索工作区。

CLI 输出单个 JSON，退出码：pass=0、warning=1、fail=2。**warning 不等于无产物**，必须同时检查 `action`、`written`：

| action | 含义 |
| --- | --- |
| `analyze` | 缺结果，调用方应转入需求分析 |
| `repair_analysis` | 唯一校验器失败，回交修正 |
| `reevaluate` | 分析过期，先重评；默认不写 |
| `register_questions` | 模板所需集合缺失有效条目，返回 `feedback` 给分析侧审阅 |
| `recover_analysis` | 存在未恢复分析事务，先由更新器恢复 |
| `inspect` | 只检查，含同步状态 |
| `draft_created` | 完整生成简化草稿；仍待产品负责人确认 |
| `inspect_write` | 保存未完整完成，保留现场供人工检查 |
| `reject` | 输入、路径或元数据错误，未进入正常生成 |

调用方只有实际完成下一步，才能称“已调用分析”或“已登记问题”；仅 action 不是执行证据。

## 草稿、元数据与文件归属

草稿保存在已有需求的 `prd/handoff-draft-vN.md`。`prd.version` 是正整数本地序号，`prd.status` 固定为 `draft`；不定义正式版本或发布流程。只替换自己维护的三字段，保留 common、其他块和 prd 扩展字段。其他格式的既有 prd 元数据拒绝覆盖。

草稿逐条保留映射、tag、status、sources、related_ids；假设附依据和验证；遗留问题保留原答案、建议和责任方。ux_assessment原样列出界面依赖、待设计、视觉建议与候选流程，并注明建议不等于既有/已实现界面。存在technical_feasibility时，另原样列出结论、证据/来源、可信程度、影响、风险和研发确认引用；技术判断不等于研发验收或发布批准。撤销条目、dropped 问题不摘录。待重评、推断和假设均有显式标注，推荐选项不是事实。

全程沿用分析工作区独占锁，非空分析事务日志阻止消费。先以排他方式写新草稿并同步，再原子提交 requirement.json。响应 `written` 表示元数据已替换，不表示每个文件均未发生写入：失败可能留下未提交草稿或 `.prd-write-*` 临时文件，返回 `inspect_write`、`draft_created` 和候选路径，保留现场、不自动删除、拒绝覆盖。即使元数据已替换，后续目录同步失败仍返回 fail，不能当成成功交付。恢复边界见规格 10.5。

## 缺口回流

`feedback` 携带 requirement_id、base_revision、missing_sections。分析侧需审阅实际缺口、查重、确定问题优先级和完成清单，然后构造 supplement 补丁，通过 `update_analysis.py` 保存。消费者不写 `analysis/`，不分配 Q 编号，不替代分析侧决定。

可调用 Python API `consume(...)`；用途、参数与异常见函数 docstring。`run_stage_4_handoff.py` 中有完整的合成接口链路，但其分析补丁不是模型自主生成。
