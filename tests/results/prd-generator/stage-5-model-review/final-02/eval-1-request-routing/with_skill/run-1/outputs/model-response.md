# 合成需求试跑结果

仅在私有工作区执行，四份需求互相独立。结果为草稿处理，不代表已完成人工评审或发布。

- **content-request — 拒绝直接改稿**：从当前筛选结果改为全部数据会改变导出范围，属于需求内容变更，应回交需求分析；未写正文或事件。
- **ambiguous-request — 拒绝直接改稿**：从用户可以导出变为系统必须自动导出，改变执行主体、触发方式和约束强度，不是可直接处理的润色，应回交需求分析；未写正文或事件。
- **layout-request — 已保存**：将 `PRD-FR-001` 的“用户可以导出当前筛选结果”改为“用户可导出当前筛选结果”，模型核对认为该句含义和规则不变。生产写入器返回 `pass`、`edited: true`，版本从 0.1 升至 0.2。
- **manual-layout — 已保存**：对照已保存基准检查整篇差异，唯一手改为 `PRD-FR-001` 的“用户可以”加粗；模型判断仅为排版、含义不变。生产写入器返回 `pass`、`edited: true`，版本从 0.1 升至 0.2，保留加粗。此处为 AI 核对，不是人工评审。

两份成功保存的 `formal_draft` 分别由写入器更新 `prd/prd.md`、`prd/prd-trace.json`、`requirement.json` 的 PRD 块及 `prd/prd-events.jsonl`；未修改分析、common 或其他元数据块。保存后检查均无待同步、正文摘要一致、未检测到未处理手改。未发布。

## 警告与遗留事项

四份初次检查及两份保存后检查均警告辅助分析事件不可用，只能按条目比较生成变更摘要，不能推断变更原因；未覆盖分析项为 `value_assessment`、`technical_feasibility`、`impact_analysis`。manual-layout 初次检查另警告正文摘要变化，保存后该警告消失。只读检查的退出码 1 对应响应中的 `warning`，`allowed` 均为 `true`，并非门禁失败。两次保存返回 `pass`、无诊断。不存在因空章节自动认定的新增缺口；保留既有遗留内容。

## 产物与执行说明

- 私有 trial：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-ab17c6bd5a2d7e52a/stage-5-trial`
- 工作区复制来源：`/home/collin/orca/PRD-Generator/workspace-sandbox/prd-generator/stage-5-model/iteration-1/request-routing/with_skill/workspace`
- 正文分别位于 `workspace/layout-request/prd/prd.md` 和 `workspace/manual-layout/prd/prd.md`，相对于上述 trial。
- 候选、逐次 JSON 响应和运行命令保存在上述 trial 的 `artifacts/`。命令分别见 `commands.sh`、`save-commands.sh`、`post-save-commands.sh`；无修正重试。

执行中协调方曾误将本任务指向另一组，随后撤回并确认原任务归属。始终使用用户指定的 `request-routing/with_skill` 与 `current-skill-snapshot`，没有读取或处理另一组；初轮因此短暂停止，纠正后完成两份明确授权的排版保存。既有检查证据未改动。
