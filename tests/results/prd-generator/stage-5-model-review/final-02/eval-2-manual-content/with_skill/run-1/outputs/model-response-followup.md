# 合成试跑后续结果

根据协调者转达的已批准模拟回答，两份均选择 B：暂时保留手改，标注与分析不一致并登记遗留事项。这是合成测试输入，不是真实业务签核或发布批准。

## manual-item

- 已保存 `PRD-FR-001` 的“导出全部数据”，在原条目和遗留事项中配对标注【与分析不一致】。遗留事项说明当前分析仅支持导出当前筛选结果，建议回交分析确认。
- 保存响应为 `warning`，`edited: true`，版本 `0.2`，实际写入正文、追溯、需求元数据的 PRD 相关部分和 PRD 事件。
- 最终文档校验警告：`SYNTHETIC-PRD/PRD-FR-001` 与分析不一致，**不得发布**。

## manual-scope

- 已保存范围章节的“允许跨租户导出”，在原章节和遗留事项中配对标注【与分析不一致】。遗留事项说明分析没有相应依据，建议回交分析确认跨租户导出及其边界。
- 保存响应为 `warning`，`edited: true`，版本 `0.2`，实际写入正文、追溯、需求元数据的 PRD 相关部分和 PRD 事件。
- 最终文档校验警告：`SYNTHETIC-PRD/prd/sections/scope` 与分析不一致，**不得发布**。

## 校验和试跑发现

- 两份首次保存候选均被拒绝，诊断为保留候选只能增加不一致标注和遗留说明，不能改写其他正文；两次失败均无写入。原因是候选替换了既有“无适用遗留项”占位。一次修正后保存成功，失败和成功候选及响应均已保留。
- 写入器要求保留原占位，因而两份正式草稿中仍存在“无适用遗留项”，与新增遗留事项表面矛盾；新增遗留说明已明确指出该原占位不再适用。这是本轮发现的文档质量问题，不能把机器校验警告当成完整语义验收。
- 保存后的只读检查显示两份均无未处理正文手改、无待同步分析，分析修订仍为 1。辅助分析事件均不可用，只能按条目比较，不推断原因。价值评估、技术可行性、影响分析仍未覆盖。
- 所有最终校验返回 `warning`、退出码 1；未修改分析或 common，未执行评审或发布。AI 判断和脚本校验不等同人工评审。

## 文件

- item 草稿：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-a97da6fc83333820e/stage-5-trial/workspace/manual-item/prd/prd.md`
- scope 草稿：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-a97da6fc83333820e/stage-5-trial/workspace/manual-scope/prd/prd.md`
- 命令、响应、候选与模拟回答来源：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-a97da6fc83333820e/stage-5-trial/artifacts/`
- 首轮说明保持不变：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-a97da6fc83333820e/stage-5-trial/outputs/model-response.md`
