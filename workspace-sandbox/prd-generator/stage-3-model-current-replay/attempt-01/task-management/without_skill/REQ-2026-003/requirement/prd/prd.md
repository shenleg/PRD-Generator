本文档基于未就绪的需求分析生成，存在未解决的阻塞问题，仅供沟通，不得作为开发或测试依据。

<!-- prd:section info -->
## 文档信息

| 字段 | 值 |
| --- | --- |
| 需求编号 | REQ-2026-003 |
| 标题 | 作业批量删除与任务删除规则 |
| PRD 版本 | 0.2 |
| 状态 | draft |
| 草稿类型 | risk_draft |
| 基于的分析修订号 | 1 |
| 生成时间 | 2026-11-17T17:05:02.804159+00:00 |
| 未覆盖的分析项 | technical_feasibility、impact_analysis |
<!-- /prd:section -->

<!-- prd:section changes -->
## 变更记录

- 2026-11-17T17:05:02.390784+00:00 · 0.1 · 首次生成工作稿（PRD-GOAL-001、PRD-SCN-001、PRD-FR-001、PRD-BR-001、PRD-BR-002、PRD-BR-003、PRD-CON-001、PRD-AC-001、PRD-FLOW-001、PRD-BND-001、PRD-BND-002、PRD-EXC-001）
- 2026-11-17T17:05:02.804159+00:00 · 0.2 · 基于同一分析输入重复生成工作稿（PRD-GOAL-001、PRD-SCN-001、PRD-FR-001、PRD-BR-001、PRD-BR-002、PRD-BR-003、PRD-CON-001、PRD-AC-001、PRD-FLOW-001、PRD-BND-001、PRD-BND-002、PRD-EXC-001）
<!-- /prd:section -->

<!-- prd:section background -->
## 背景与目标

<!-- prd:item PRD-GOAL-001 -->
**PRD-GOAL-001** 提供对选中作业的批量删除；需求来源未说明更具体的价值原因。 依据：REQ-2026-003/GOAL-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section scope -->
## 范围

本稿共同讨论批量删除、删除权限及既有删除处理，避免遗漏其相互关系；不把作业和任务视为已经确认的同一对象。
<!-- /prd:section -->

<!-- prd:section scenarios -->
## 场景

<!-- prd:item PRD-SCN-001 -->
**PRD-SCN-001** 用户选中作业后点击删除；相关角色及授权存在冲突。 依据：REQ-2026-003/SCN-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section functional_requirements -->
## 功能需求

<!-- prd:item PRD-FR-001 -->
**PRD-FR-001** 支持选中作业后批量删除；跨页选择及删除后的数据状态未定义。 依据：REQ-2026-003/FR-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section business_rules -->
## 业务规则

未列为已确认规则的细节均需澄清，不应推定。

<!-- prd:item PRD-BR-001 -->
**PRD-BR-001** 原文称批量删除所有用户均可操作；该陈述与另一删除权限陈述存在待解冲突，不作为最终授权。 依据：REQ-2026-003/BR-1
<!-- /prd:item -->

<!-- prd:item PRD-BR-002 -->
**PRD-BR-002** 原文称工程创建者和管理员可以删除任务，其他人只能看；适用对象与前述作业是否相同待确认。 依据：REQ-2026-003/BR-2
<!-- /prd:item -->

<!-- prd:item PRD-BR-003 -->
**PRD-BR-003** 删除按之前逻辑处理，但旧逻辑未提供；不能推断软硬删除、结果保留或运行中处理。 依据：REQ-2026-003/BR-3
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section flows_states -->
## 流程

<!-- prd:item PRD-FLOW-001 -->
**PRD-FLOW-001** 【推断】【待确认】已知动作仅为选中作业并点击删除；权限识别、执行处理及结果呈现是待确认的候选流程。 依据：REQ-2026-003/FLOW-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section boundaries_exceptions -->
## 边界与异常

<!-- prd:item PRD-BND-001 -->
**PRD-BND-001** 【推断】运行中对象能否删除、对执行及结果的影响未知；不默认停止任务或软删除。 依据：REQ-2026-003/BND-1
<!-- /prd:item -->

<!-- prd:item PRD-BND-002 -->
**PRD-BND-002** 【推断】未选、跨页、筛选变更、混合权限及对象已被删除时，实际选中和删除集合待定义。 依据：REQ-2026-003/BND-2
<!-- /prd:item -->

<!-- prd:item PRD-EXC-001 -->
**PRD-EXC-001** 【推断】部分对象不可删除、权限或状态变化、部分失败及重复操作时，整批拒绝还是部分成功待定。 依据：REQ-2026-003/EXC-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section constraints -->
## 约束及非功能

<!-- prd:item PRD-CON-001 -->
**PRD-CON-001** 要求尽快上线，本期尽量不影响仿真引擎；不是硬期限或绝对禁止引擎变更。 依据：REQ-2026-003/CON-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section acceptance_criteria -->
## 验收草案

<!-- prd:item PRD-AC-001 -->
**PRD-AC-001** 【推断】【待确认】待对象关系、授权、删除效果及批量失败策略确认后，验证授权与未授权用户对选中集合的操作及关联结果，覆盖运行中、对象不存在、混合权限和重复执行。 依据：REQ-2026-003/AC-1
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

<!-- prd:residual REQ-2026-003/AC-1 -->
REQ-2026-003/AC-1【推断】待确认对象关系、授权、删除效果及批量失败策略后，分别用授权与未授权用户对确定选中集合执行删除，核对每个对象和关联结果的最终状态；覆盖运行中、已不存在、混合权限及重复执行。现在不能判定删除成功，故仅作验收草案。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/FR-2 -->
REQ-2026-003/FR-2【推断】合并分析批量删除、删除权限和既有删除处理规则，以避免将同一删除动作拆出相互矛盾的结论；‘作业’与‘任务’是否同对象仍待确认，不代表已合并领域概念。未获得任何本期明确排除项。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/FLOW-1 -->
REQ-2026-003/FLOW-1【推断】原文仅可还原选中作业、点击删除。候选完整流程还需识别对象与权限、执行已确认删除处理、呈现各项结果；这些不是已确认的产品流程。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/BND-1 -->
REQ-2026-003/BND-1【推断】候选关键边界：选择中含仍在运行的任务时，删除是否允许、是否影响正在执行的仿真与已产生结果未知。不能因‘尽量不影响引擎’就推断只能软删除或一定可以停止任务。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/BND-2 -->
REQ-2026-003/BND-2【推断】候选边界：未选对象、跨页或筛选变化后选择是否保留、选择中混有无权限或已被他人删除的对象。必须界定实际删除集合，避免误删未选择对象。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/EXC-1 -->
REQ-2026-003/EXC-1【推断】候选异常：一批对象中部分不允许删除、执行时权限或状态变化、部分失败及重复点击。整批拒绝还是允许部分成功尚未确定，不能以成功提示掩盖未删除或被误删对象。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/GAP-1 -->
REQ-2026-003/GAP-1【推断】缺少既有删除规则及删除后的可判定业务结果，无法知道是否删除记录、关联结果、是否可恢复及对运行任务的影响。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/CNF-1 -->
REQ-2026-003/CNF-1【推断】删除权限存在待解决的重大冲突：第2条说作业批量删除所有用户可操作，第5条说只有工程创建者和管理员可删任务；若两词同指或操作重叠，两规则不能同时成立。即便对象不同，也必须明确各自授权范围，不能默认无冲突。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-1 -->
REQ-2026-003/Q-1 P0 待答：针对‘选中后点击删除’这个操作，最终应允许哪些用户执行？若作业与任务权限不同，请分别指出。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-2 -->
REQ-2026-003/Q-2 P0 待答：‘按之前逻辑’的删除最终应对任务记录和关联仿真结果产生什么效果？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-3 -->
REQ-2026-003/Q-3 P0 待答：本文‘作业’与‘任务’是什么关系？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-4 -->
REQ-2026-003/Q-4 P0 待答：仍在运行的任务应允许执行删除吗？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-5 -->
REQ-2026-003/Q-5 P0 待答：一批选中对象中有不能删除或删除失败的对象时，整批结果应如何判定？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-6 -->
REQ-2026-003/Q-6 P0 待答：批量删除的‘选中’集合如何限定？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-7 -->
REQ-2026-003/Q-7 P0 待答：提供第6条所指之前的删除逻辑，尤其是对象、状态限制、数据保留和失败处理条款。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-8 -->
REQ-2026-003/Q-8 P1 待答：新增批量删除主要希望解决什么问题？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-9 -->
REQ-2026-003/Q-9 P1 待答：请研发核实既有删除机制、权限校验、运行任务与结果依赖、并发及重复执行保护，并评估引擎影响。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-003/Q-10 -->
REQ-2026-003/Q-10 P1 待答：提供现有任务页中选择与删除的相关页面资料。
<!-- /prd:residual -->

<!-- prd:residual /ux_assessment/design_pending_items/0 -->
界面待定：现有任务页未提供；业务规则确认后确定选择、范围提示和删除结果反馈，不以界面设计替代删除语义
<!-- /prd:residual -->
<!-- /prd:section -->

<!-- prd:section appendix -->
## 来源

依据：本需求 analysis/analysis-result.json，分析修订 1；源资料以 analysis/source-manifest.json 为准。
<!-- /prd:section -->
