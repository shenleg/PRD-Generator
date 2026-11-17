本文档基于未就绪的需求分析生成，存在未解决的阻塞问题，仅供沟通，不得作为开发或测试依据。

<!-- prd:section info -->
## 文档信息

| 字段 | 值 |
| --- | --- |
| 需求编号 | REQ-2026-005 |
| 标题 | 仿真结果表格导出 |
| PRD 版本 | 0.1 |
| 状态 | draft |
| 草稿类型 | risk_draft |
| 基于的分析修订号 | 1 |
| 生成时间 | 2026-11-17T16:25:01.065529+00:00 |
| 未覆盖的分析项 | technical_feasibility、impact_analysis |
<!-- /prd:section -->

<!-- prd:section changes -->
## 变更记录

- 2026-11-17T16:25:01.065529+00:00 · 0.1 · 首次生成工作稿（PRD-GOAL-001、PRD-SCN-001、PRD-FR-001、PRD-BR-001、PRD-BR-002、PRD-CON-001、PRD-CON-002、PRD-AC-001、PRD-FLOW-001、PRD-BND-001、PRD-BND-002、PRD-BND-003、PRD-EXC-001、PRD-EXC-002）
<!-- /prd:section -->

<!-- prd:section background -->
## 背景与目标

<!-- prd:item PRD-GOAL-001 -->
**PRD-GOAL-001** 改善仿真结果导出不方便的问题，提供表格导出。 依据：REQ-2026-005/GOAL-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section scope -->
## 范围

本稿覆盖结果表格、字段、格式、数量和完整性；不将全部解释为所有用户的结果，也不凭空排除其他格式。
<!-- /prd:section -->

<!-- prd:section scenarios -->
## 场景

<!-- prd:item PRD-SCN-001 -->
**PRD-SCN-001** 用户导出仿真结果；单任务、所选任务或其他范围，以及任务是否必须完成均未确定。 依据：REQ-2026-005/SCN-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section functional_requirements -->
## 功能需求

<!-- prd:item PRD-FR-001 -->
**PRD-FR-001** 仿真结果应能以表格导出常用字段；字段、行粒度与文件格式待确认。 依据：REQ-2026-005/FR-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section business_rules -->
## 业务规则

未列为已确认规则的细节均需澄清，不应推定。

<!-- prd:item PRD-BR-001 -->
**PRD-BR-001** 原文称最多导出1000条；这是数量冲突的一方，不可自行认定为最终截断规则。 依据：REQ-2026-005/BR-1
<!-- /prd:item -->

<!-- prd:item PRD-BR-002 -->
**PRD-BR-002** 原文又称数据量大时导出全部结果、不要丢数据；全部的对象、授权及时间范围尚未定义。 依据：REQ-2026-005/BR-2
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section flows_states -->
## 流程

<!-- prd:item PRD-FLOW-001 -->
**PRD-FLOW-001** 【推断】【待确认】候选流程为选定有权结果范围、发起导出、等待并取得表格；范围、权限和输出内容均待确认。 依据：REQ-2026-005/FLOW-1
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section boundaries_exceptions -->
## 边界与异常

<!-- prd:item PRD-BND-001 -->
**PRD-BND-001** 【推断】未完成或失败任务的部分结果能否导出待定，不能将仿真结果直接等同于已完成最终结果。 依据：REQ-2026-005/BND-1
<!-- /prd:item -->

<!-- prd:item PRD-BND-002 -->
**PRD-BND-002** 【推断】可导出的工程、任务及字段范围未知；删除权限不能自动推广为导出权限。 依据：REQ-2026-005/BND-2
<!-- /prd:item -->

<!-- prd:item PRD-BND-003 -->
**PRD-BND-003** 【推断】空结果、恰好1000条和超过1000条均需确认处理；大量数据的等待及超时策略未知。 依据：REQ-2026-005/BND-3
<!-- /prd:item -->

<!-- prd:item PRD-EXC-001 -->
**PRD-EXC-001** 【推断】读取、生成或下载部分失败时，成功与部分成功如何判定待定义，不能静默漏行。 依据：REQ-2026-005/EXC-1
<!-- /prd:item -->

<!-- prd:item PRD-EXC-002 -->
**PRD-EXC-002** 【推断】导出期间数据或权限变化时，全部结果对应的时间点待确认；不假定已有快照能力。 依据：REQ-2026-005/EXC-2
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section constraints -->
## 约束及非功能

<!-- prd:item PRD-CON-001 -->
**PRD-CON-001** 格式需与之前的报告一致；旧报告缺失，不能指定 CSV、XLSX 或固定列。 依据：REQ-2026-005/CON-1
<!-- /prd:item -->

<!-- prd:item PRD-CON-002 -->
**PRD-CON-002** 尽快上线且本期尽量不影响仿真引擎；没有硬期限或绝对禁改引擎的约束。 依据：REQ-2026-005/CON-2
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section acceptance_criteria -->
## 验收草案

<!-- prd:item PRD-AC-001 -->
**PRD-AC-001** 【推断】【待确认】待对象、数量、权限、内容及一致性确认后，按已知有权结果集逐行核对字段和格式；覆盖空结果、1000条、超1000条、未完成、权限不足、数据变化和部分失败。 依据：REQ-2026-005/AC-1
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

<!-- prd:residual REQ-2026-005/AC-1 -->
REQ-2026-005/AC-1【推断】待业务规则确认后，以已知且有权导出的结果集逐项核对表格行、字段和格式，覆盖空结果、1000条、超过1000条、未完成任务、权限不足、数据变化与部分失败，验证没有静默截断或漏行。缺少对象、数量、权限、内容和一致性规则，现仅为待重评草案。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/FR-2 -->
REQ-2026-005/FR-2【推断】本需求涵盖仿真结果的表格导出、字段、格式、数量与完整性边界，不把‘全部’延伸为所有用户的结果。未明确提出的格式或导出方式不自动视为已排除。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/FLOW-1 -->
REQ-2026-005/FLOW-1【推断】候选流程为用户选定有权访问的结果范围、发起导出、等待生成并取得表格。对象范围、权限、生命周期、数量及输出内容未确定，不能据此声称完整流程已知。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/BND-1 -->
REQ-2026-005/BND-1【推断】候选关键边界：任务尚未完成、失败或只有部分结果时能否导出。‘仿真结果’不等于已完成的最终结果；若允许未完成导出，必须区分当时结果与完整最终结果。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/BND-2 -->
REQ-2026-005/BND-2【推断】候选关键边界：用户可导出的工程、任务和结果字段范围未知。删除角色规则不能自动推广到导出，‘全部结果’不代表跨工程或跨用户无授权访问。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/BND-3 -->
REQ-2026-005/BND-3【推断】候选数量边界包括空结果、恰好1000条及超过1000条。大量数据可能需要较长生成与下载时间，等待、超时或分批策略未知；没有提供规模上限，不编造阈值或默认截断。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/EXC-1 -->
REQ-2026-005/EXC-1【推断】候选异常：部分结果读取失败、生成或下载中断，得到部分文件却被当成成功会违反不丢数据诉求。需要可判定的成功、失败或明确部分成功语义，不能静默漏行。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/EXC-2 -->
REQ-2026-005/EXC-2【推断】候选一致性边界：导出期间结果继续产生、被删除或权限变化时，‘全部’的时间点不明，可能漏项、重复或混合不同时点的数据。快照或其他规则需确认，不自行假定有现成快照能力。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/GAP-1 -->
REQ-2026-005/GAP-1【推断】缺少导出对象范围、常用字段清单及旧报告内容，无法确定每行含义、必备列或格式一致性的判定方式。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/CNF-1 -->
REQ-2026-005/CNF-1【推断】当结果超过1000条时，‘最多1000条’与‘数据量大就导出全部、不要丢数据’无法直接同时执行；不能擅自把1000解释成分页、分文件单位或自动忽略上限。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-1 -->
REQ-2026-005/Q-1 P0 待答：结果超过1000条时，最终应该导出多少条？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-2 -->
REQ-2026-005/Q-2 P0 待答：一次导出的结果对象范围是什么？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-3 -->
REQ-2026-005/Q-3 P0 待答：‘常用字段’中哪些列是本期必需，含义及行粒度是什么？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-4 -->
REQ-2026-005/Q-4 P0 待答：提供备注所指之前的报告或导出格式规范，并明确对应版本。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-5 -->
REQ-2026-005/Q-5 P0 待答：用户可导出哪些工程或任务的结果，是否存在不可导出的字段？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-6 -->
REQ-2026-005/Q-6 P0 待答：任务未完成或失败时，是否允许导出已产生的结果？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-7 -->
REQ-2026-005/Q-7 P0 待答：导出过程中数据可能变化时，‘全部结果’以哪个时点为准？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-8 -->
REQ-2026-005/Q-8 P0 待答：部分结果无法导出时，什么结果可以被标为导出成功？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-9 -->
REQ-2026-005/Q-9 P1 待答：结果为空时应如何反馈？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-10 -->
REQ-2026-005/Q-10 P1 待答：大量结果无法在一次短等待内生成时，用户应得到哪种后续处理？
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-11 -->
REQ-2026-005/Q-11 P1 待答：请研发核实结果存储与访问控制、旧报告导出能力、大量生成/下载限制、时点一致性及中断恢复能力，并评估引擎影响。
<!-- /prd:residual -->

<!-- prd:residual REQ-2026-005/Q-12 -->
REQ-2026-005/Q-12 P1 待答：提供现有任务页中结果及导出入口的相关资料。
<!-- /prd:residual -->

<!-- prd:residual /ux_assessment/design_pending_items/0 -->
界面待定：现有任务页资料未提供；导出入口、范围提示、生成等待及失败反馈待业务确认后设计，文件格式另受旧报告约束
<!-- /prd:residual -->
<!-- /prd:section -->

<!-- prd:section appendix -->
## 来源

依据：本需求 analysis/analysis-result.json，分析修订 1；源资料以 analysis/source-manifest.json 为准。
<!-- /prd:section -->
