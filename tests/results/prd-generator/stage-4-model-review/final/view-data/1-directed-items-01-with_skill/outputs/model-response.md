# 三份定向同步结果

## 执行范围与结果

私有 trial 绝对路径：
`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af79ced9e5e7b0d3f/trial-stage4-directed`

已完成 PG-14、PG-16、PG-32-tag 三个独立场景的实际同步。先确认私有 worktree 路径，再将用户指定只读输入复制为本 trial 的 `workspace`；只读指定生产 Skill 及本 trial 对应场景资料。未委派、提交、发布、修改产品实现，未读取其他模型结果、人工参考或测试源码。未写主 checkout，未写 analysis；元数据由统一保存入口更新 PRD 管理块。

每个场景依次执行 `check_sync`、以独立补丁调用只读 `assign_ids`、`write_draft --sync` 和最后一次 `validate_prd`。生产脚本均从可信私有 worktree 根按用户指定的 uv / 隔离 Python 方式单独运行。

| 场景 | generated / synced | 实际版本与类型 | written | 最终 validate_prd |
| --- | --- | --- | --- | --- |
| PG-14 | true / true | 0.1 → 0.2，formal_draft，draft，分析修订 1 → 2 | 5 个文件 | pass，diagnostics=[] |
| PG-16 | true / true | 0.1 → 0.2，formal_draft，draft，分析修订 1 → 2 | 5 个文件 | pass，diagnostics=[] |
| PG-32-tag | true / true | 0.1 → 0.2，formal_draft，draft，分析修订 1 → 2 | 5 个文件 | pass，diagnostics=[] |

三个成功响应的 written 列表均为对应需求目录下：`prd/prd.md`、`prd/prd-trace.json`、`prd/gap-requests.json`、`requirement.json`、`prd/prd-events.jsonl`。这些是脚本实际报告的写入，不是只生成候选。没有评审或发布。

## 实际定向变化

### PG-14

仅改写 PRD-FR-001 的受影响业务文本为“合成查询只返回条件匹配记录，不代表真实业务”。PRD-FR-002 的原始条目字节、编号及既有身份保留；其他业务章节不润色、不重排。无新增编号、无缺口关闭、无适用遗留项。

正式正文：
`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af79ced9e5e7b0d3f/trial-stage4-directed/workspace/PG-14/prd/prd.md`

### PG-16

独立补丁新增 SYNTHETIC-PRD/FR-3 映射，采用 assign_ids 实际返回的 PRD-FR-003，正文加入“新增合成统计功能”。未复用废止的 PRD-FR-001；该身份继续保留为 abolished，不回到有效章节。PRD-FR-002 保持原始条目字节和编号。其他业务章节保持原文。无缺口关闭、无适用遗留项。

正式正文：
`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af79ced9e5e7b0d3f/trial-stage4-directed/workspace/PG-16/prd/prd.md`

### PG-32-tag

SYNTHETIC-PRD/FR-1 业务句子未变，仅因权威标签 confirmed → inferred，在 PRD-FR-001 加【推断】，并在遗留章节以完整来源引用和 residual 定位块列出待验证内容。未将推断升级为已确认事实，也未因 readiness=ready_for_document 删除推断遗留项。PRD-FR-002 原始条目字节和编号保留，其余无关业务章节不变。无新增编号、无缺口关闭。

首次 write_draft 因遗留项缺少机器定位标记失败：rule 8，`prd.md/residuals`，generated=false，written=[]，退出码 2。只修正一次，补齐 `prd:residual SYNTHETIC-PRD/FR-1` 成对标记，使用新的候选文件和新的 candidate-dir 后成功；未再次同步成功结果。失败正文、失败候选目录和失败 JSON 均保留。

正式正文：
`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af79ced9e5e7b0d3f/trial-stage4-directed/workspace/PG-32-tag/prd/prd.md`

## 全部警告与兼容处理

三份 check_sync 均为 pass、allowed=true、pending=true、diagnostics=[]；各章 category=unknown，section_basis_available=false，不将 unknown 当作 unchanged。

三份成功 write_draft 均返回 status=warning、退出码 1，但 generated=true、synced=true，且 written 非空。唯一诊断相同：

> 旧稿缺少章节依据证据，未自动证明这些章节的最小同步；需补旧分析或人工逐章核对：acceptance_criteria、appendix、background、boundaries_exceptions、business_rules、constraints、flows_states、functional_requirements、impact、residuals、scenarios、scope、technical、ux

按兼容规则接受并保留此警告，未补造旧分析、未把当前分析冒充旧依据。已人工逐章对照当前权威分析与所读旧 PRD：现有 scope、scenarios、business_rules、boundaries_exceptions、acceptance_criteria 均无分析内容，保持旧文字；附录保留 SRC-1；缺省可选分析章节不臆造；功能章节只作上述定向变化；遗留章节仅 PG-32-tag 增加推断待验证项；info 和 changes 交脚本渲染。机器校验不证明旧章节历史依据或自然语言语义充分性。

三份缺省辅助资料均为 `value_assessment`、`technical_feasibility`、`impact_analysis`，已由保存入口登记未覆盖分析项，未补写价值、技术或历史影响结论。ui_dependent=false，不生成界面章节。

三份原 gaps 都为空，未创建或关闭任何 GAPREQ，也未将任何 handed_over 误判为已补足。

## 归档材料

以下路径均在本 trial 下，未另外制作正文/追溯/缺口副本，直接归档 workspace 中正式产物即可：

- `workspace/PG-14/prd/`、`workspace/PG-16/prd/`、`workspace/PG-32-tag/prd/`：正式正文、追溯、缺口及事件。
- `patches/PG-14.json`、`patches/PG-16.json`、`patches/PG-32-tag.json`：独立映射补丁。
- `candidates/PG-14.md`、`candidates/PG-16.md`、`candidates/PG-32-tag.md`、`candidates/PG-32-tag-retry-1.md`：模型实际正文候选，含保留的失败稿。
- `artifacts/PG-14`、`artifacts/PG-16`、`artifacts/PG-32-tag-retry-1`：成功保存入口候选材料；`artifacts/PG-32-tag` 保留首次失败材料。
- `outputs/PG-14/`、`outputs/PG-16/`、`outputs/PG-32-tag/`：逐文件用 Write 保存的实际 check_sync、assign_ids、write_draft、validate_prd JSON 响应；PG-32-tag 另有 `write-draft-attempt-1.json`。

三份最终校验完成即收束，未扩展检查或重复同步。
