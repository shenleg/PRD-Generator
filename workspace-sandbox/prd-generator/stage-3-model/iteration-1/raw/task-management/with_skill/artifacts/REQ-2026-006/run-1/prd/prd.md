本文档基于未就绪的需求分析生成，存在未解决的阻塞问题，仅供沟通，不得作为开发或测试依据。

<!-- prd:section info -->
## 文档信息

| 字段 | 值 |
| --- | --- |
| 需求编号 | REQ-2026-006 |
| 标题 | 任务结束通知 |
| PRD 版本 | 0.1 |
| 状态 | draft |
| 草稿类型 | risk_draft |
| 基于的分析修订号 | 1 |
| 生成时间 | 2026-11-17T16:56:35.861594+00:00 |
| 未覆盖的分析项 | technical_feasibility、impact_analysis |
<!-- /prd:section -->

<!-- prd:section changes -->
## 变更记录

- 2026-11-17T16:56:35.861594+00:00 · 0.1 · 首次生成工作稿（PRD-GOAL-001、PRD-SCN-001、PRD-FR-001、PRD-FR-002、PRD-CON-001、PRD-AC-001、PRD-FLOW-001、PRD-BND-001、PRD-BND-002、PRD-EXC-001）
<!-- /prd:section -->

<!-- prd:section background -->
# 背景与价值
要求在任务跑完后通知用户，具体新增动因尚未说明。 未提供量化价值结论。
<!-- /prd:section -->

<!-- prd:section scope -->
# 目标与范围
<!-- prd:item PRD-GOAL-001 -->PRD-GOAL-001：在任务跑完后通知用户；具体要解决的问题未说明。 分析来源：REQ-2026-006/GOAL-1。<!-- /prd:item -->

<!-- prd:item PRD-FR-002 -->PRD-FR-002：【推断】独立分析结束通知，不合并到状态显示；触发含义需与最终确认的结束语义一致。其他通知场景不视为已排除。 分析来源：REQ-2026-006/FR-2。<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section scenarios -->
# 用户与场景
<!-- prd:item PRD-SCN-001 -->PRD-SCN-001：任务跑完后某类用户收到通知；接收者是提交者、工程创建者、关注者还是其他人未说明。 分析来源：REQ-2026-006/SCN-1。<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section functional_requirements -->
# 功能需求
| 编号 | 内容 | 分析来源 |
| --- | --- | --- |
| <!-- prd:item PRD-FR-001 -->PRD-FR-001 | 任务跑完后发送通知；触发状态、对象、渠道、内容与送达预期未给出。 | REQ-2026-006/FR-1<!-- /prd:item --> |
<!-- /prd:section -->

<!-- prd:section business_rules -->
# 业务规则
分析结果中无此项。
<!-- /prd:section -->

<!-- prd:section flows_states -->
# 流程与状态
<!-- prd:item PRD-FLOW-001 -->PRD-FLOW-001：【推断】【待确认】候选流程为任务达到已确认结束条件、识别有权接收者、通过已确认渠道发送并识别任务与结果；这些规则仍未确认。 分析来源：REQ-2026-006/FLOW-1。<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section boundaries_exceptions -->
# 边界与异常
<!-- prd:item PRD-BND-001 -->PRD-BND-001：【推断】失败、取消、重试再结束及重复事件是否触发、属于同一次完成与否尚待规则；不能固定发送次数。 分析来源：REQ-2026-006/BND-1。<!-- /prd:item -->

<!-- prd:item PRD-BND-002 -->PRD-BND-002：【推断】接收者离开工程、无法访问任务或通知含敏感结果时，接收对象与可见内容需匹配；不能援引删除权限默认通知可见性。 分析来源：REQ-2026-006/BND-2。<!-- /prd:item -->

<!-- prd:item PRD-EXC-001 -->PRD-EXC-001：【推断】用户离线、渠道不可用或发送失败时是否重试、记录失败未定；不假设现有通知平台或重试次数。 分析来源：REQ-2026-006/EXC-1。<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section constraints -->
# 约束与非功能需求
<!-- prd:item PRD-CON-001 -->PRD-CON-001：尽快上线且本期尽量不影响仿真引擎；没有硬期限，也未确定通知机制。 分析来源：REQ-2026-006/CON-1。<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section acceptance_criteria -->
# 验收条件
| 编号 | 内容 | 分析来源 |
| --- | --- | --- |
| <!-- prd:item PRD-AC-001 -->PRD-AC-001 | 【推断】【待确认】确认触发、对象、渠道和内容后，分别测试应通知及不应通知的状态，核对正确接收者在指定渠道收到可识别任务与结果的通知；覆盖重复事件、权限变化和发送失败。送达预期尚不能判定。 | REQ-2026-006/AC-1<!-- /prd:item --> |
<!-- /prd:section -->

<!-- prd:section ux -->
# 界面与交互
具体设计资料与待确认事项见遗留事项；不能据此假定现有界面或渠道。
<!-- /prd:section -->

<!-- prd:section technical -->
# 研发确认项
未开展技术可行性评估，具体研发核实事项见遗留事项。
<!-- /prd:section -->

<!-- prd:section residuals -->
# 遗留事项
<!-- prd:residual REQ-2026-006/Q-1 -->REQ-2026-006/Q-1：P0，ask_product，open：‘任务跑完’具体包含哪些应发通知的结束结果？ 建议（尚未采纳）：推荐B作为讨论起点，使用户能发现执行失败；原文没有确认失败也算跑完，不自动采用。 影响：可能漏发失败任务通知或在尚未真正结束时误发。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-2 -->REQ-2026-006/Q-2：P0，ask_product，open：任务结束通知应发给谁？ 建议（尚未采纳）：推荐A作为最小接收范围的讨论起点，不默认为工程内所有用户。 影响：可能通知错误对象或泄露任务信息，核心送达对象不明确。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-3 -->REQ-2026-006/Q-3：P0，ask_product，open：本期通知采用哪个渠道？ 建议（尚未采纳）：推荐A作为不增加外部联络数据的讨论起点；是否已有站内能力由研发确认，不视为已存在。 影响：决定核心用户接收路径，不是单纯视觉细节。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-4 -->REQ-2026-006/Q-4：P0，ask_product，open：通知中最低必须包含哪些业务信息？ 建议（尚未采纳）：推荐A，先形成最小有效通知，避免默认向消息正文带出仿真结果明细。 影响：用户可能不知道哪个任务结束或看到无权访问的数据。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-5 -->REQ-2026-006/Q-5：P1，ask_product，open：重复结束事件或任务重试后再次结束，应如何计算通知次数？ 建议（尚未采纳）：推荐A作为候选规则，既防重复也不漏掉新的执行结果；任务是否支持重试仍需研发核实，场景不存在时再判断问题是否不成立。 影响：影响通知的完整性和可验证触发规则。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-6 -->REQ-2026-006/Q-6：P1，ask_product，open：通知发送失败时应采取哪种业务处理？ 建议（尚未采纳）：推荐A作为讨论起点，重试边界待业务与研发确认，不编造次数或时间。 影响：影响失败可见性和恢复预期。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-7 -->REQ-2026-006/Q-7：P1，ask_product，open：新增结束通知主要希望解决什么问题？ 建议（尚未采纳）：请按实际动因确认，不能把任一候选原因当原文事实。 影响：帮助判断通知的必要范围，不否定用户的明确功能诉求。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-8 -->REQ-2026-006/Q-8：P1，ask_dev，open：请研发核实可用的结束事件与通知基础能力、接收权限校验、去重和失败处理，并评估引擎影响。 影响：决定最终业务规则的实现与验证手段。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/GAP-1 -->REQ-2026-006/GAP-1：【推断】‘跑完’是否只指成功、也包含失败或取消尚不明确；不得直接把任意状态结束都作为通知触发条件。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/GAP-2 -->REQ-2026-006/GAP-2：【推断】通知接收对象、渠道和最低有效内容都缺失，无法确定‘给用户发个通知’是否完成；不能默认为任务提交者的站内信。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/FR-2 -->REQ-2026-006/FR-2：【推断】独立分析结束通知，不合并到状态显示；触发含义需与最终确认的结束语义一致。其他通知场景不视为已排除。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/AC-1 -->REQ-2026-006/AC-1：【推断】【待确认】确认触发、对象、渠道和内容后，分别测试应通知及不应通知的状态，核对正确接收者在指定渠道收到可识别任务与结果的通知；覆盖重复事件、权限变化和发送失败。送达预期尚不能判定。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/FLOW-1 -->REQ-2026-006/FLOW-1：【推断】【待确认】候选流程为任务达到已确认结束条件、识别有权接收者、通过已确认渠道发送并识别任务与结果；这些规则仍未确认。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/BND-1 -->REQ-2026-006/BND-1：【推断】失败、取消、重试再结束及重复事件是否触发、属于同一次完成与否尚待规则；不能固定发送次数。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/BND-2 -->REQ-2026-006/BND-2：【推断】接收者离开工程、无法访问任务或通知含敏感结果时，接收对象与可见内容需匹配；不能援引删除权限默认通知可见性。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/EXC-1 -->REQ-2026-006/EXC-1：【推断】用户离线、渠道不可用或发送失败时是否重试、记录失败未定；不假设现有通知平台或重试次数。<!-- /prd:residual -->

<!-- prd:residual /ux_assessment/design_pending_items/0 -->/ux_assessment/design_pending_items/0：通知是用户可感知交互，载体和渠道未定；ui_dependent不表示已经选定站内通知或某个任务页组件，待渠道确定后才明确必要设计资料<!-- /prd:residual -->
<!-- /prd:section -->

<!-- prd:section appendix -->
# 附录
领域词汇：任务跑完（触发状态未定义）、用户（接收对象未定义）、通知（渠道未定义）。来源：SRC-1。未开展历史需求对照。
<!-- /prd:section -->
