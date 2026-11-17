# 真实 Skill 试跑结果

四个独立合成场景均已完成增量同步：PRD `0.1 → 0.2`，分析基准修订 `1 → 2`，状态仍为 `draft`，门禁类型为 `formal_draft`。这不代表人工确认、已评审或获准发布。每个场景最终 `validate_prd.py` 为 `pass`，`check_sync.py` 为 `pass`、`pending=false`，诊断均为空。

## 路径调整与执行边界

执行中协调线程要求遵守 worktree 隔离，故将原始工作区输入复制到私有 trial 后继续，未将同步结果回写共享工作稿。

- 本次完整私有 trial：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps`
- 权威生产 Skill 快照：`/home/collin/orca/PRD-Generator/workspace-sandbox/prd-generator/stage-4-model/iteration-1/current-skill-snapshot`
- 初始输入快照：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/artifacts/initial-workspace`
- 调整前仅在原共享 run 的 `artifacts/<场景>/check-sync.before.json`、`check-sync.before.stderr` 保存了四场景只读响应；原共享 workspace 未改变，既有共享证据未删除或覆盖。
- 命令从可信的当前 worktree 调用给定 Skill 的绝对生产脚本路径，采用指定的离线 `uv` 与 `python -I -B`，未在输入目录运行解释器，未自行实现同步或编号器。

## 逐场景实况

### PG-31-retain-answer：同步完成，拒绝关闭缺口

- 原缺口 `GAPREQ-1`：查询功能的验收条件尚缺；唯一接收问题为 `SYNTHETIC-PRD/Q-1`。
- 虽然 Q-1 为 `answered`，回答仅为“已收到回复；仍须核实有效分析条目，不能只凭这句关闭”。实际 `acceptance_criteria` 仍为空，亦无不再需要的明确决策或范围依据，FR-1 的功能描述不能替代验收条件。
- 因此原请求仍为 `handed_over`，缺口描述、登记版本、计数器、扩展字段及原验收占位保持，遗留事项补充保留理由。建议回需求分析，由产品按原问题补足可核对的验收条件。
- 无正式编号新增、修改、废止或待确认；就绪度仍为 `ready_for_document`，不自行改写分析。
- 最终副本目录：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/outputs/PG-31-retain-answer`

### PG-31-supplied：同步完成，按 supplied 关闭缺口

- 同一原缺口的唯一接收问题 Q-1 已回答。当前有效、`confirmed` 的 `SYNTHETIC-PRD/AC-1` 实际规定“查询只返回与输入条件匹配的记录”，并关联 FR-1，已提供原缺失的查询验收条件。
- 据此将 GAPREQ-1 置为 `closed`，`resolution.kind=supplied`，引用 AC-1 并说明覆盖关系；移除原占位，以实际验收内容替换。
- 使用生产 `assign_ids.py` 返回的 `PRD-AC-001`，统一入口将引入版本保存为 `0.2`。原功能编号及内容不变。
- 本场景分析无其他应列遗留事项；并非仅凭回答或交接状态关闭。
- 最终副本目录：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/outputs/PG-31-supplied`

### PG-31-not-needed：同步完成，按 not_needed 关闭缺口

- 唯一接收问题 Q-1 已回答。当前有效的范围排除项 `SYNTHETIC-PRD/FR-3` 明确记录“本期不扩展查询验收，该模板验收信息不再需要”，这是权威分析给出的不再需要依据，不是生成器自行作出的范围决策。
- 据此关闭 GAPREQ-1，`resolution.kind=not_needed` 引用 FR-3；移除唯一占位，在范围、验收及遗留说明中保留该依据，不把范围排除项导入为新功能，也不臆造验收条件。
- 无正式编号新增、修改、废止或待确认；查询及导出条目保持不变。
- 最终副本目录：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/outputs/PG-31-not-needed`

### PG-31-provisional：一次修正后同步完成，暂定补足仍保留验证

- 唯一接收问题 Q-1 为 `provisional`。有效的 `SYNTHETIC-PRD/AC-1` 以 `assumption` 提供“查询只返回与输入条件匹配的记录”，并关联 FR-1、ASM-1；`SYNTHETIC-PRD/ASM-1` 提供对应假设、依据及验证方式。
- 将 GAPREQ-1 按 `supplied` 关闭，引用 AC-1、ASM-1，只表示缺失信息有了暂定补足，不是确认验收口径。正文 `PRD-AC-001` 保留【暂定】，追溯标签仍为 `assumption`。
- 遗留章节继续定位 Q-1（P1、ask_product、provisional，推荐先补分析）及 ASM-1；依据为“产品尚待核对验收口径”，验证方式为“产品后续核对验收样例”。
- 首轮统一保存被拒绝：规则 8，ASM-1、Q-1 在 `prd.md/residuals` 缺少遗留项机器定位。首轮已有语义说明，但未加 `prd:residual` 标记；响应 `written=[]`、`generated=false`，目录对比证实正式文件未改。
- 保留全部首轮候选与响应，重新检查门禁，第二轮只补定位标记及同一假设的交叉说明，保存成功。共修正 1 次，未超限。
- 失败响应：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/artifacts/PG-31-provisional/write-draft.attempt-1.json`
- 失败候选目录：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/artifacts/PG-31-provisional/validated-candidate.attempt-1`
- 成功响应：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/artifacts/PG-31-provisional/write-draft.attempt-2.json`
- 最终副本目录：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/outputs/PG-31-provisional`

以上各最终副本目录均含 `prd.md`、`prd-trace.json`、`gap-requests.json` 三份文件；对应私有 `workspace/<场景>/prd/` 保留正式同步文件及追加事件。

## 警告、未覆盖内容与保留核对

- 最终工具未返回 warning/fail 诊断。四场景均缺省 `value_assessment`、`technical_feasibility`、`impact_analysis`，已由保存入口列入文档信息的未覆盖分析项；未编造价值、技术或历史需求对照结论。
- `retain-answer` 的信息缺口仍未解决；`provisional` 的验收口径仍待产品核验。`formal_draft` 来自当前权威分析的就绪度，不应将其当作实际业务已完成或人工批准。
- 四场景旧正式条目 `PRD-FR-001`、`PRD-FR-002` 连同标记、章节、编号、内容保持原始字节；旧追溯的映射、标签、状态、来源摘要及引入版本 `0.1` 未改。只有 supplied、provisional 各在其独立场景新增工具分配的 `PRD-AC-001`。
- 所有 analysis 目录与初始快照逐文件比较无差异；`requirement.json` 的 diff 只含 `prd.based_on_analysis_revision` 和 `prd.version` 更新，`common` 及 `other_owner` 块不变。缺口身份、描述、登记版本、计数器及扩展字段保留。
- 工具统一渲染文档信息与变更记录，未顺带润色其他正文。四份 `final-changes.diff` 保留实际变化供核对。
- 未修改产品实现，未读人工参考、测试源码、preparation-only、expected 或其他运行/模型输出；未委派，未发布、安装、提交或推送。初始仅只读确认当前目录已有 Git 仓库。

## 证据位置

- 工具响应、stderr、候选正文、独立编号补丁、完整 gap 候选、工具生成候选及修正过程：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/artifacts/<场景>/`
- 各场景最终检查：上述目录内 `validate.final.json`、`check-sync.final.json`。
- 各场景保留核对：上述目录内 `final-changes.diff`、`analysis-unchanged.diff`、`metadata.diff`。
- 执行事实及路径调整记录：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/artifacts/execution-record.json`
- 本说明：`/home/collin/orca/PRD-Generator/.claude/worktrees/agent-af28332f3be0f7c98/trial-stage4-gaps/outputs/model-response.md`
