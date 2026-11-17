# PRD Generator 阶段 0 候选材料

本目录登记两组候选样例的原文、分析快照和阶段 1 夹具计划，不创建生产 Schema 或正式 PRD。

## 候选样例

| 组别 | 原文 | 建议固定的分析输入 | 当前状态 |
| --- | --- | --- | --- |
| 高低压开关组合 | `tests/fixtures/high-low-voltage/original-requirement.md` | `REQ-2026-001` 首轮修订 `1` | 已于 `2026-11-17` 采用并认可生成侧参考 |
| 仿真任务管理优化 | `tests/fixtures/sample-02-task-management.md` | `REQ-2026-002`～`REQ-2026-006` 各自首轮修订 `1`，以删除需求 `REQ-2026-003` 为重点 | 已于 `2026-11-17` 采用并认可生成侧参考 |

准确路径、元数据及原文件 SHA-256 见 `sample-catalog.json`。该文件是开发准备清单，不是分析侧或生成侧的生产数据协议。

选择首轮已保存快照，是为了不混入后续模拟答复、更正和新版重评。第二组五份分析分别对应五个需求，不擅自合并；两组均为 `not_ready`，仅适合作为风险草稿及忠实性检查的自然样例，其他就绪度和发布场景另备合成输入。

## 已执行与未执行

- 当前分析校验器已对六份候选快照实际执行，均为 `pass / 0`。原始响应见 `tests/results/prd-generator/stage-0-sample-validation.json`。
- 校验前后来源指纹相同；没有修改历史分析、原文或旧参考要点。
- 这些结果不证明正式 PRD 生成器已实现，不等于业务就绪或人工认可。
- 本目录只登记现有文件，不复制或移动历史快照。原来源清单包含当前环境绝对路径；以后跨环境试跑时另建工作副本，显式记录路径重定位，不改旧证据。

## 后续材料入口

- `stage-1-fixture-plan.md`：全部校验规则的合法夹具及反例计划，协议未确认前不填生产 JSON。
- `tests/scenarios/prd-generator/README.md`：`PG-01`～`PG-34` 唯一完整验收阶段。
- `tests/expected/prd-generator/high-low-voltage.review-draft.md`：第一组参考要点草案。
- `tests/expected/prd-generator/task-management.review-draft.md`：第二组参考要点草案。
- `tests/results/prd-generator/stage-0.md`：实际进展、人工确认和退出条件。

样例采用与参考要点认可均来自本次用户明确选择，原始答案和被认可草案指纹见 `tests/results/prd-generator/stage-0-decisions.json`，不是由材料或模型自行授予。准备清单保留初始来源指纹，执行计划因用户确认更新的前后指纹单独登记。
