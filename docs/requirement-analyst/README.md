# Requirement Analyst 文档

本目录收纳需求分析 Skill 的现行维护文档；生产源码仍在 `skill/requirement-analyst/`，路径均以仓库根目录为基准，Markdown 链接按文件位置解析。

| 内容 | 入口 |
| --- | --- |
| 能力、数据格式和交接规则 | [规格](spec.md) |
| 阶段目标、步骤及退出条件 | [执行计划](execution-plan.md) |
| 安装、自动触发及既有验证范围 | [安装与调用](installation.md) |
| 第二组样例的设计说明 | [仿真任务管理样例](sample-task-management.md) |
| 测试代码、重放入口和历史证据 | [测试导航](../../tests/requirement-analyst/README.md) |
| 最终验收及未完成事项 | [历史验收报告](../../tests/results/final-acceptance.md) |

阶段 1～8及最终收口已经提交到 `main`。历史报告中“尚未提交”等文字是当时状态，当前提交以 Git 为准；本次只归类，不重写历史报告。

真实下游 Skill 联调原获批准延期；生成 Skill 具备后按双侧接口补验。八项量化指标的统一基线与阈值、真实业务签核仍不能由现有程序回归代替。
