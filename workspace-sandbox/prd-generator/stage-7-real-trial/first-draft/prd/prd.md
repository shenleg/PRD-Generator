草稿，待产品经理确认后发布。

<!-- prd:section info -->
## 文档信息

| 字段 | 值 |
| --- | --- |
| 需求编号 | REQ-2026-001 |
| 标题 | 统一仓库能力状态与验收证据入口 |
| PRD 版本 | 0.1 |
| 状态 | draft |
| 草稿类型 | formal_draft |
| 基于的分析修订号 | 1 |
| 生成时间 | 2026-11-18T03:20:29.917170+00:00 |
| 未覆盖的分析项 | technical_feasibility |
<!-- /prd:section -->

<!-- prd:section changes -->
## 变更记录

- 2026-11-18T03:20:29.917170+00:00 · 0.1 · 首次生成工作稿（PRD-GOAL-001、PRD-SCN-001、PRD-FR-001、PRD-FR-002、PRD-BR-001、PRD-BR-002、PRD-BR-003、PRD-CON-001、PRD-CON-002、PRD-FLOW-001、PRD-BND-001、PRD-BND-002、PRD-BND-003、PRD-AC-001、PRD-AC-002、PRD-AC-003、PRD-AC-004）
<!-- /prd:section -->

<!-- prd:section background -->
## 背景与价值

根 README 对生成侧状态前后矛盾，两个 Skill 的阶段编号又相互独立，新协作者难以判断各自能力、验证范围和验收依据。

本需求希望让首次接手仓库的协作者和维护者从统一入口找到两个 Skill 的能力摘要、详细状态和证据，减少状态表述矛盾及不同验证层次的混称。业务价值等级未评定；通过本稿验收条件检查结果，未约定量化指标。
<!-- /prd:section -->

<!-- prd:section scope -->
## 目标与范围

<!-- prd:item PRD-GOAL-001 -->
**PRD-GOAL-001**：让维护者和首次接手的协作者从根 README 找到两个 Skill 的当前能力、验证范围、未验证事项和可信证据，并减少同一入口前后矛盾。

分析来源：`REQ-2026-001/GOAL-1`
<!-- /prd:item -->

本期范围与不包含事项见“约束与非功能需求”。
<!-- /prd:section -->

<!-- prd:section scenarios -->
## 用户与场景

<!-- prd:item PRD-SCN-001 -->
**PRD-SCN-001**：新协作者或维护者从根 README 查看两个 Skill 的能力摘要，沿导航进入对应详细状态，再查找可追溯的验收依据和未验证事项。

分析来源：`REQ-2026-001/SCN-1`
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section functional_requirements -->
## 功能需求

| 编号 | 内容 | 分析来源 |
| --- | --- | --- |
| <!-- prd:item PRD-FR-001 -->PRD-FR-001 | 根 README 只承载两个 Skill 的能力状态摘要和导航；详细状态分别由两个 Skill 自己的文档承载。 | `REQ-2026-001/FR-1`<!-- /prd:item --> |
| <!-- prd:item PRD-FR-002 -->PRD-FR-002 | 各 Skill 的详细状态按主要能力说明已实现、已验证、已人工验收及未验证范围，并提供可追溯的证据入口，不逐条复制测试清单。 | `REQ-2026-001/FR-2`<!-- /prd:item --> |
<!-- /prd:section -->

<!-- prd:section business_rules -->
## 业务规则

<!-- prd:item PRD-BR-001 -->
**PRD-BR-001**：已验证须能区分程序回归与实际模型证据；已实现、已验证、已人工验收和未验证不得混称。隔离合成发布不算真实业务发布，草稿、格式校验和阶段验收也不等同于正式发布批准。

分析来源：`REQ-2026-001/BR-1`
<!-- /prd:item -->

<!-- prd:item PRD-BR-002 -->
**PRD-BR-002**：两个 Skill 的阶段编号各自独立，不能用分析侧阶段 7 代表生成侧阶段 7 的双 Skill 联调。

分析来源：`REQ-2026-001/BR-2`
<!-- /prd:item -->

<!-- prd:item PRD-BR-003 -->
**PRD-BR-003**：各 Skill 维护者更新各自的详细状态，仓库入口维护者核对根 README 的摘要。

分析来源：`REQ-2026-001/BR-3`
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section flows_states -->
## 流程与状态

<!-- prd:item PRD-FLOW-001 -->
**PRD-FLOW-001**：维护交接中，各 Skill 维护者更新所属详细状态；仓库入口维护者核对根 README 摘要。具体触发机制和自动化方式未约定。

分析来源：`REQ-2026-001/FLOW-1`
<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section boundaries_exceptions -->
## 边界与异常

<!-- prd:item PRD-BND-001 -->
**PRD-BND-001**：基线 `7b016bf` 的生成侧阶段 6 原记录表明，十项场景有程序剧本验证，独立实际模型证据仅覆盖记录中的两组；该阶段结果已获人工认可。该原记录还说明，截至记录时未发生真实业务 PRD 发布，也未开始生成侧阶段 7 正式双 Skill 联调。这些是该基线记录的证据范围，不作为当前状态断言。

分析来源：`REQ-2026-001/BND-1`
<!-- /prd:item -->

<!-- prd:item PRD-BND-002 -->
**PRD-BND-002**：分析侧阶段 7 记录的是体验与图像调用，分析侧阶段 8 记录受控知识沉淀；这些记录不等同于生成侧阶段 7 的正式双 Skill 联调。

分析来源：`REQ-2026-001/BND-2`
<!-- /prd:item -->

<!-- prd:item PRD-BND-003 -->
**PRD-BND-003**：未约定自动化更新、每项详细能力状态是否必须分别链接原始日志、具体实现方案、人员姓名或正式发布；这些事项不作为已确认规则。

分析来源：`REQ-2026-001/BND-3`
<!-- /prd:item -->

### 异常

分析结果中无此项。
<!-- /prd:section -->

<!-- prd:section constraints -->
## 约束与非功能需求

### 本期范围

<!-- prd:item PRD-CON-001 -->
**PRD-CON-001**：本需求面向现有仓库的 Markdown 能力状态、证据导航和维护交接；本轮只分析并交给文档生成，不实施原件改造。

分析来源：`REQ-2026-001/CON-1`
<!-- /prd:item -->

### 本期不包含

<!-- prd:item PRD-CON-002 -->
**PRD-CON-002**：不要求建设新系统、重跑旧验收、改写历史证据或实际发布业务 PRD；本次试用不修改指定输入原件。

分析来源：`REQ-2026-001/CON-2`
<!-- /prd:item -->

### 非功能需求

分析结果中无此项。
<!-- /prd:section -->

<!-- prd:section acceptance_criteria -->
## 验收条件

| 编号 | 内容 | 分析来源 |
| --- | --- | --- |
| <!-- prd:item PRD-AC-001 -->PRD-AC-001 | 检查根 README：能从能力摘要分别导航到两个 Skill 的详细状态；根入口摘要与对应详细状态及同页说明不再互相矛盾。 | `REQ-2026-001/AC-1`<!-- /prd:item --> |
| <!-- prd:item PRD-AC-002 -->PRD-AC-002 | 检查各 Skill 详细状态：按主要能力能区分已实现、已验证、已人工验收和未验证；已验证能区分程序回归与实际模型证据，证据可追溯，且不将合成发布标为真实业务发布、不混用两个 Skill 的阶段编号。 | `REQ-2026-001/AC-2`<!-- /prd:item --> |
| <!-- prd:item PRD-AC-003 -->PRD-AC-003 | 检查交接说明：能识别各 Skill 维护者更新各自详细状态、仓库入口维护者核对根 README 摘要的责任分工；不将未约定的自动化更新写成既定要求。 | `REQ-2026-001/AC-3`<!-- /prd:item --> |
| <!-- prd:item PRD-AC-004 -->PRD-AC-004 | 检查生成侧阶段 6 的状态表述：不把两组实际模型证据扩称为十项场景均有模型覆盖，不把隔离合成发布或阶段人工认可写成真实业务发布。基线 `7b016bf` 的阶段 6 原记录称当时尚未开始阶段 7 正式双 Skill 联调；不得将该记录表述为当时联调已完成，也不能据此断言当前状态。 | `REQ-2026-001/AC-4`<!-- /prd:item --> |
<!-- /prd:section -->

<!-- prd:section impact -->
## 关联与影响

受影响的文档范围包括根 README 的状态摘要和导航，以及 `requirement-analyst`、`prd-generator` 各自的详细状态文档。

后续文档工作应消除根入口现状矛盾，保持摘要与详细状态一致；按主要能力组织状态和证据入口，保留实际覆盖范围与未验证边界，并记录维护责任。自动化、逐项原始日志链接及具体实现方案不作为既定要求。

已人工对照指定的四份固定资料；未执行带采用指纹的正式历史检索或分析基线对照，因此不能据此声称其他历史资料不存在冲突。技术可行性分析未覆盖，未形成技术可行性结论。
<!-- /prd:section -->

<!-- prd:section residuals -->
## 遗留事项

<!-- prd:residual REQ-2026-001/GAP-1 -->
**`REQ-2026-001/GAP-1` — 基线文档现状缺陷**：基线根 README 的状态表称生成侧评审和发布尚未实现，同页安装与使用部分却称阶段 6 已增加评审、发布、废弃及发布后另建工作稿。生成侧文档入口和阶段 6 记录支持后者所述的阶段 6 实现范围。后续文档改造应消除摘要与详细状态的矛盾，不改写历史证据。该条是有来源的现状缺陷，不是缺失的业务信息。

来源：`SRC-2` 按 Skill 查找及安装与使用；`SRC-3` 阶段进度说明；`SRC-5` 实施及阶段退出；本轮用户确认根 README 的矛盾是现状。
<!-- /prd:residual -->
<!-- /prd:section -->

<!-- prd:section appendix -->
## 附录

### 术语

已实现、程序回归、实际模型证据、已人工验收、未验证、真实业务发布。

### 输入资料

下列仓库资料固定于资料基线 `7b016bf`；来源定位以分析条目为准。

| 来源 | 输入原件 |
| --- | --- |
| `SRC-1` | `input/brief.md`：真实试用原始需求 |
| `SRC-2` | `input/source/README.md`：基线根 README |
| `SRC-3` | `input/source/docs/prd-generator/README.md`：PRD Generator 文档入口 |
| `SRC-4` | `input/source/docs/requirement-analyst/installation.md`：需求分析 Skill 安装说明 |
| `SRC-5` | `input/source/tests/results/prd-generator/stage-6.md`：PRD Generator 阶段 6 记录 |

用户本轮确认分别记录在相关分析条目的 `user_answer` 来源中。
<!-- /prd:section -->
