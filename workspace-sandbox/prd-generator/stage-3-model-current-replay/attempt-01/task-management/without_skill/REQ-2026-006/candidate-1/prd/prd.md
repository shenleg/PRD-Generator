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
| 生成时间 | 2026-11-17T17:05:06.538273+00:00 |
| 未覆盖的分析项 | technical_feasibility、impact_analysis |
<!-- /prd:section -->

<!-- prd:section changes -->
## 变更记录

- 2026-11-17T17:05:06.538273+00:00 · 0.1 · 首次生成工作稿（PRD-GOAL-001、PRD-SCN-001、PRD-FR-001、PRD-CON-001、PRD-AC-001、PRD-FLOW-001、PRD-BND-001、PRD-BND-002、PRD-EXC-001）
<!-- /prd:section -->

<!-- prd:section background -->
## 背景与目标

<!-- prd:item PRD-GOAL-001 -->
**PRD-GOAL-001** 任务跑完后向用户发送通知；原文未说明更具体的价值原因。 依据：REQ-2026-006/GOAL-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section scope -->
## 范围

本稿独立讨论任务结束通知；触发语义需与状态需求最终确认的结束语义一致，不代表排除其他通知。
<!-- /prd:section -->

<!-- prd:section scenarios -->
## 场景

<!-- prd:item PRD-SCN-001 -->
**PRD-SCN-001** 任务结束后某类用户收到通知；接收者身份尚未确定。 依据：REQ-2026-006/SCN-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section functional_requirements -->
## 功能需求

<!-- prd:item PRD-FR-001 -->
**PRD-FR-001** 任务跑完后发送通知；触发状态、接收对象、渠道、内容及送达预期待确认。 依据：REQ-2026-006/FR-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section business_rules -->
## 业务规则

未列为已确认规则的细节均需澄清，不应推定。
<!-- /prd:section -->

<!-- prd:section flows_states -->
## 流程

<!-- prd:item PRD-FLOW-001 -->
**PRD-FLOW-001** 【推断】【待确认】候选流程为达到确认的结束条件、识别有权接收者、通过确认渠道发送；各环节尚未确定。 依据：REQ-2026-006/FLOW-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section boundaries_exceptions -->
## 边界与异常

<!-- prd:item PRD-BND-001 -->
**PRD-BND-001** 【推断】失败、取消、重试再次结束及重复事件是否触发通知、次数如何计算均待定。 依据：REQ-2026-006/BND-1
<!-- /prd:item -->

<!-- prd:item PRD-BND-002 -->
**PRD-BND-002** 【推断】接收者离开工程、任务不可访问或通知包含敏感结果时，接收权限与可见内容待确认。 依据：REQ-2026-006/BND-2
<!-- /prd:item -->

<!-- prd:item PRD-EXC-001 -->
**PRD-EXC-001** 【推断】用户不在线、渠道不可用或发送失败时的记录、重试及业务处理未规定。 依据：REQ-2026-006/EXC-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section constraints -->
## 约束及非功能

<!-- prd:item PRD-CON-001 -->
**PRD-CON-001** 尽快上线，本期尽量不影响仿真引擎；未给出硬期限或通知实现机制。 依据：REQ-2026-006/CON-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section acceptance_criteria -->
## 验收草案

<!-- prd:item PRD-AC-001 -->
**PRD-AC-001** 【推断】【待确认】待触发、对象、渠道及内容确认后，分别核对应通知和不应通知的任务，以及重复事件、权限变化和发送失败；目前不能判定送达预期。 依据：REQ-2026-006/AC-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section ux -->
## 交互待定

现有界面资料不足，交互方案待业务规则确认后确定。
<!-- /prd:section -->

<!-- prd:section technical -->
## 技术可行性

技术可行性未覆盖；需研发核实现有能力与引擎影响。
<!-- /prd:section -->

<!-- prd:section impact -->
## 影响分析

影响分析未覆盖；需确认范围和依赖。
<!-- /prd:section -->

<!-- prd:section residuals -->
## 遗留事项

<!-- prd:residual REQ-2026-006/AC-1 -->
REQ-2026-006/AC-1【推断】待确认触发、对象、渠道和内容后，让测试任务分别达到应通知和不应通知的状态，核对正确接收者在指定渠道获得可识别任务及结果的通知，并覆盖重复事件、接收权限变化和发送失败。当前只能形成待重评草案，不能判定核心送达预期。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/FR-2 -->
REQ-2026-006/FR-2【推断】独立分析任务结束后的通知行为，不将其与任务状态显示合成同一功能；触发语义需要与状态需求最终确认的结束语义一致。其他通知场景未被明确提出，也不记为用户已排除。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/FLOW-1 -->
REQ-2026-006/FLOW-1【推断】候选流程为任务达到已确认结束条件、识别有权接收的对象、通过已确认渠道发送、用户可识别对应任务和结束结果。当前触发、对象、渠道和内容都未确认，不能当作完整流程。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/BND-1 -->
REQ-2026-006/BND-1【推断】候选关键边界：任务失败、取消、重试后再次结束或重复结束事件，通知是否触发及是否属于同一次完成需要规则；‘跑完’语义未明前不能固定发送次数。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/BND-2 -->
REQ-2026-006/BND-2【推断】候选权限边界：发送时接收者已离开工程、任务不可访问，或通知带出敏感结果内容。通知对象与可看内容应匹配，不能因删除权限条款而默认任何人可看通知。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/EXC-1 -->
REQ-2026-006/EXC-1【推断】候选异常：用户不在线、渠道不可用或发送失败，可能错过通知；是否重试、是否明确记录失败尚未规定。不推断已有通知平台或任意重试次数。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/GAP-1 -->
REQ-2026-006/GAP-1【推断】‘跑完’是否只指成功、也包含失败或取消尚不明确；不得直接把任意状态结束都作为通知触发条件。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/GAP-2 -->
REQ-2026-006/GAP-2【推断】通知接收对象、渠道和最低有效内容都缺失，无法确定‘给用户发个通知’是否完成；不能默认为任务提交者的站内信。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-1 -->
REQ-2026-006/Q-1 P0 待答：‘任务跑完’具体包含哪些应发通知的结束结果？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-2 -->
REQ-2026-006/Q-2 P0 待答：任务结束通知应发给谁？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-3 -->
REQ-2026-006/Q-3 P0 待答：本期通知采用哪个渠道？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-4 -->
REQ-2026-006/Q-4 P0 待答：通知中最低必须包含哪些业务信息？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-5 -->
REQ-2026-006/Q-5 P1 待答：重复结束事件或任务重试后再次结束，应如何计算通知次数？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-6 -->
REQ-2026-006/Q-6 P1 待答：通知发送失败时应采取哪种业务处理？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-7 -->
REQ-2026-006/Q-7 P1 待答：新增结束通知主要希望解决什么问题？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-006/Q-8 -->
REQ-2026-006/Q-8 P1 待答：请研发核实可用的结束事件与通知基础能力、接收权限校验、去重和失败处理，并评估引擎影响。
<!-- /prd:residual -->

<!-- prd:residual /ux_assessment/design_pending_items/0 -->
界面待定：通知是用户可感知交互，载体和渠道未定；ui_dependent不表示已经选定站内通知或某个任务页组件，待渠道确定后才明确必要设计资料
<!-- /prd:residual -->
<!-- /prd:section -->

<!-- prd:section appendix -->
## 来源

依据：本需求 analysis/analysis-result.json，分析修订 1；源资料以 analysis/source-manifest.json 为准。
<!-- /prd:section -->
