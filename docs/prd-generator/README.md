# PRD Generator 文档

本目录收纳需求文档生成 Skill 的现行规格与执行计划。代码位于 `skill/prd-generator/`，测试维护代码位于 `tests/prd-generator/`。

| 内容 | 入口 |
| --- | --- |
| 完整形态、格式与交接协议 | [规格](spec.md) |
| 阶段 0～7的实施顺序和退出条件 | [执行计划](execution-plan.md) |
| 测试与合成格式证据 | [测试导航](../../tests/prd-generator/README.md) |
| 首稿、门禁、编号、恢复及只读校验 | [脚本说明](../../skill/prd-generator/scripts/README.md) |
| 上游能力和接口 | [分析侧文档](../requirement-analyst/README.md) |

阶段 0～3 已验收，原确认、日志和来源指纹保持原样；分析侧缺口接收范围见 [阶段 2 记录](../../tests/results/prd-generator/stage-2.md)。阶段 3 的入口、门禁、正式编号、信息渲染和统一草稿保存已完成程序及实际模型验证，并获用户最终草稿试用认可，见 [阶段 3 记录](../../tests/results/prd-generator/stage-3.md)。

新增写入职责先经用户确认再补规格；参考、草稿试用和指标决定分别留证。其余阈值本轮只记录，由用户在阶段 7 真实试用前确定，规格硬规则不放宽。同步、编辑、评审和发布仍未实现，不称为完整生命周期交付；未自动进入阶段 4。提交及合并状态以 Git 历史为准，不自动提交或合并。
