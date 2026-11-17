# PRD Generator 文档

本目录收纳需求文档生成 Skill 的现行规格与执行计划。代码位于 `skill/prd-generator/`，测试维护代码位于 `tests/prd-generator/`。

| 内容 | 入口 |
| --- | --- |
| 完整形态、格式与交接协议 | [规格](spec.md) |
| 阶段 0～7的实施顺序和退出条件 | [执行计划](execution-plan.md) |
| 测试与合成格式证据 | [测试导航](../../tests/prd-generator/README.md) |
| 只读校验器使用方式 | [脚本说明](../../skill/prd-generator/scripts/README.md) |
| 上游能力和接口 | [分析侧文档](../requirement-analyst/README.md) |

阶段 0、1已完成并合入 `main`；生成侧格式和只读校验器已具备，但当前没有 `SKILL.md`、正式编号写入、同步器或发布器，不能称为完整生成 Skill。

阶段 2 的分析侧缺口接收配套补丁及本阶段验收已完成，范围见 [阶段 2 记录](../../tests/results/prd-generator/stage-2.md)，提交及合并状态以 Git 历史为准。原确认、测试日志和来源指纹保持原样；没有进入阶段 3。
