# 测试与模型试跑

本目录区分格式测试、Skill 静态契约检查和已保存的模型行为试跑。Python 测试只读产物，不调用模型或产生额外 API 费用。

## 自动检查

在仓库根目录执行：

```bash
uv run --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests -p 'test_*.py' -v
```

- `test_schemas.py`、`test_validate_analysis.py`、`test_report_template.py`：阶段 1 格式与校验器回归。
- `test_skill_contract.py`：阶段 2 的入口、引用和测试材料检查，不能代替实际模型行为。
- `test_stage_2_runs.py`：读取已保存的真实模型输出，检查正式样例的校验、拆分、状态、提问与结束；另从只读响应日志核对探针的轻量价值分析。所声明执行方式对应的证据缺失必须失败，不静默跳过。

## 行为试跑的依据和输入

- 人工已审核的参考要点位于 `expected/`，适用范围与审核记录写在各文件开头。
- 场景剧本位于 `scenarios/RA-xx.md`，包含输入、分轮回答和核对清单。
- 只有 `fixtures/` 中的需求原文或合成探针可以交给被测模型，不能交给它参考答案、黄金结果或预设的后续回答。
- 合成探针只验证提问策略，不代表用户真实系统或产品决定。测试中的模拟 user_answer 不作为正式需求确认。

## 本阶段如何执行模型

本阶段使用当前执行环境中的独立模型会话，显式读取 Skill 源码及其按需引用；调用方只指定测试编号、项目、输出目录和轮次配置。没有新增 API 客户端、API Key 或自动批量收费脚本。

这是显式加载源码的行为试跑，不是安装后斜杠命令或自动触发的集成测试。模型必须保留实际输出，主会话按照已审核要点和确定性的程序断言核对，不接受模型自报“场景 pass”作为证据。

执行环境禁止子模型写 Markdown 报告后，用户已明确批准调整分工：子模型只做业务分析 JSON 和对话，主会话独立使用 `render_trial_reports.py` 校验正式 JSON 并整理报告。该工具仅为测试数据视图，不随 Skill 安装、不补充业务规则。缺少报告的原子试跑仍按 partial 保留，不冒充单一子模型的端到端通过。

模型试跑产物位于 `workspace-sandbox/stage-2/`，由 `run-manifest.json` 的 attempt 选择当前 `attempt-NN/`；旧尝试保留，不用旧文件混成新一次输出。以下目录均相对当前尝试：

- `high-low-voltage/`：第一样例及上限/结束分支。
- `task-management/`：第二样例拆分结果与逐轮澄清；首轮结果保留在 `snapshots/turn-01/`。
- `probes/idea/`：有正式 JSON 的模糊想法探针。其余后端、缺陷与价值探针改为纯只读会话，实际响应记录在 `tests/results/stage-2-text-probes.json`，不要求或宣称已有正式 JSON。
- 各需求的正式结果、报告及清单保存在 `requirements/<编号>/analysis/`；候选 JSON 不作为正式结果读取。
- `turn-NN.json` 保存实际 assistant_message、asked_question_refs、control_questions 及当前输入来源。只登记的问题不等于本轮实际提问。

上一级的 `run-manifest.json` 记录 Skill、校验器及输入的 SHA-256。相关文件变化后，旧产物不能继续证明新版本行为已通过，需要重新试跑，而不是只重写哈希。

本阶段最后一次修改仅新增导出专用检查段落，已对受影响的 REQ-2026-005 实际执行内部重评并保存 turn-04。`scoped_rechecks` 保留精确新增文字、修改前后哈希、适用范围和真实响应/校验路径；测试核对移除该唯一段落即可还原原版。这个记录只证明对应范围已重评，不代表所有非导出输入重新盲跑。超出该精确范围的后续变更仍必须重新运行相关行为场景。

## 分轮与计分

先保存并核对首轮，才按实际问到的语义提供剧本回答；用户的结束要求单独作为后续输入。未发生的回答不能提前混入结果。第一样例的上限控制确认和业务问题分别说明，但所有发生提问的轮次均计入记录。

场景共用一次实际运行时，记录各自检查的不同性质，不虚构为多次独立试跑。结果及无效问题的具体判定保存在 `results/stage-2.md`；没有实际证据的项保持未完成，不因为文件存在就记 pass。
