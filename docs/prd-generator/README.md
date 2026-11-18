# PRD Generator 文档

本页维护文档生成 Skill 的现行能力状态、验收证据和使用入口。生产源码位于 [`skill/prd-generator/`](../../skill/prd-generator/)。

## 能力与验收

**生成侧核心阶段 0～7 全部通过验收。** [最终验收报告](../../tests/results/prd-generator/final-acceptance.md)记录 `PG-01`～`PG-34` 的程序回归（双侧共 `486` 项），并单列实际模型、人工认可和真实业务发布的不同状态。

| 已实现的能力 | 程序或 CLI 验证 | 实际模型证据与人工验收范围 |
| --- | --- | --- |
| 格式校验、草稿门禁、编号与首稿追溯 | [格式校验](../../tests/results/prd-generator/stage-1.md)及[首稿记录](../../tests/results/prd-generator/stage-3.md)覆盖输入门禁、生成写入和编号稳定。 | 两组样例实际生成并获人工试用认可；样例结果不代表真实业务批准。 |
| 增量同步、编号保留与缺口核实 | [缺口接收](../../tests/results/prd-generator/stage-2.md)及[同步记录](../../tests/results/prd-generator/stage-4.md)覆盖受限接收、定向更新和按实际依据关闭缺口。 | 阶段 4 的实际模型试跑与当前源码重放分别留证，用户认可同步范围和缺口处理。 |
| 内容与排版分流、手工修改检测 | [阶段 5 记录](../../tests/results/prd-generator/stage-5.md)覆盖编辑保存、保留标记和分析侧边界。 | 实际试跑、发现问题后的重放和最终人工认可分别记录。 |
| 评审、退回、发布门禁、废弃和不可变快照 | [生成侧阶段 6](../../tests/results/prd-generator/stage-6.md)以程序剧本验证十项场景，包括不满足条件时拒发和发布后另建工作稿。 | 独立实际模型证据仅覆盖两组生命周期对照，获人工认可；并非十项全有模型覆盖。测试中的确认和定稿均属隔离合成流程。 |
| 双 Skill 安装、交接与并发拒写 | [生成侧阶段 7](../../tests/results/prd-generator/stage-7.md)覆盖安装态脚本、正式缺口闭环、文件归属、旧候选拒写及重读。 | [宿主调用证据](../../tests/results/prd-generator/stage-7-host-evidence.json)记录直接调用、自然语言自动触发和同会话承接。真实需求首稿与 `0.2` 定向同步已获[人工认可](../../tests/results/prd-generator/stage-7-final-approval.json)。 |

**未验证或未执行的范围**：没有发布真实业务 PRD。真实试用认可针对工作稿及联调结果，不是产品经理的发布确认；无样本的指标不判满分，小样本结果不外推。分析侧阶段 7 的体验与图像证据见[分析侧能力状态](../requirement-analyst/README.md#能力与验收)，不计为生成侧双 Skill 联调证据。

## 使用与维护

| 内容 | 入口 |
| --- | --- |
| 完整形态、格式与交接协议 | [规格](spec.md) |
| 阶段 0～7 的实施顺序和退出条件 | [执行计划](execution-plan.md) |
| 并列安装、依赖和调用方式 | [双 Skill 安装说明](installation.md) |
| 公开 CLI、测试与证据重放 | [脚本说明](../../skill/prd-generator/scripts/README.md) · [测试导航](../../tests/prd-generator/README.md) |

每次生成侧阶段通过人工验收后，由生成 Skill 维护者更新本页详细状态及证据入口，仓库入口维护者核对[根 README](../../README.md) 摘要。阶段记录和原始指纹保留，不以旧报告当时的状态覆盖现行结论。
