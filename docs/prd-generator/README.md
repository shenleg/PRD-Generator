# PRD Generator 文档

本目录收纳需求文档生成 Skill 的现行规格与执行计划。代码位于 `skill/prd-generator/`，测试维护代码位于 `tests/prd-generator/`。

| 内容 | 入口 |
| --- | --- |
| 完整形态、格式与交接协议 | [规格](spec.md) |
| 阶段 0～7的实施顺序和退出条件 | [执行计划](execution-plan.md) |
| 并列安装、依赖和调用方式 | [双 Skill 安装说明](installation.md) |
| 测试与合成格式证据 | [测试导航](../../tests/prd-generator/README.md) |
| 首稿、门禁、编号、恢复及只读校验 | [脚本说明](../../skill/prd-generator/scripts/README.md) |
| 上游能力和接口 | [分析侧文档](../requirement-analyst/README.md) |

阶段 0～3 已验收，原确认、日志和来源指纹保持原样；分析侧缺口接收范围见 [阶段 2 记录](../../tests/results/prd-generator/stage-2.md)。阶段 3 的入口、门禁、正式编号、信息渲染和统一草稿保存已完成程序及实际模型验证，并获用户最终草稿试用认可，见 [阶段 3 记录](../../tests/results/prd-generator/stage-3.md)。

新增写入职责先经用户确认再补规格；参考、草稿试用和指标决定分别留证。其余阈值本轮只记录，由用户在阶段 7 真实试用前确定，规格硬规则不放宽。阶段 4 的只读比较、未发布工作稿增量同步及缺口核实已完成，并获用户最终语义认可，证据及旧稿章节降级边界见 [阶段 4 记录](../../tests/results/prd-generator/stage-4.md)。阶段 5 编辑分流、手工修改检测及坚持保留标注已完成程序、实际模型及当前源码重放验证，并获用户最终语义认可，见 [阶段 5 记录](../../tests/results/prd-generator/stage-5.md) 和 [最终认可](../../tests/results/prd-generator/stage-5-final-approval.json)。阶段 6 已实现评审、发布、废弃和发布后工作稿；开发及验收进展见[阶段 6 记录](../../tests/results/prd-generator/stage-6.md)。阶段 7 的隔离安装、正式双 Skill 联调和真实试用已获用户最终验收；生成侧核心阶段 0～7 全部通过，见[最终验收报告](../../tests/results/prd-generator/final-acceptance.md)。未进行真实业务发布；提交及合并状态以 Git 历史为准，不自动提交或合并。
