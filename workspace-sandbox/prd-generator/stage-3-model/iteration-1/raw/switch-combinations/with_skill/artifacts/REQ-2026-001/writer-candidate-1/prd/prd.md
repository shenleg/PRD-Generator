本文档基于未就绪的需求分析生成，存在未解决的阻塞问题，仅供沟通，不得作为开发或测试依据。

<!-- prd:section info -->
## 文档信息

| 字段 | 值 |
| --- | --- |
| 需求编号 | REQ-2026-001 |
| 标题 | 架构图高低压开关组合逻辑设计表 |
| PRD 版本 | 0.1 |
| 状态 | draft |
| 草稿类型 | risk_draft |
| 基于的分析修订号 | 1 |
| 生成时间 | 2026-11-17T16:21:58.678669+00:00 |
| 未覆盖的分析项 | technical_feasibility、impact_analysis |
<!-- /prd:section -->

<!-- prd:section changes -->
## 变更记录

- 2026-11-17T16:21:58.678669+00:00 · 0.1 · 首次生成工作稿（PRD-GOAL-001、PRD-SCN-001、PRD-FR-001、PRD-FR-002、PRD-FR-003、PRD-FR-004、PRD-FLOW-001、PRD-BND-001、PRD-BND-002、PRD-EXC-001、PRD-AC-001、PRD-AC-002）
<!-- /prd:section -->

<!-- prd:section background -->
# 背景与价值
工程师手工整理开关动作逻辑设计表效率低、容易出错。本需求希望改善这一问题；分析未提供量化收益指标。（REQ-2026-001/GOAL-1）
<!-- /prd:section -->

<!-- prd:section scope -->
# 目标与范围
<!-- prd:item PRD-GOAL-001 -->PRD-GOAL-001：在架构仿真平台的架构图中增加高低压开关组合逻辑设计表，改善人工整理效率低和易出错的问题。（REQ-2026-001/GOAL-1）<!-- /prd:item -->

<!-- prd:item PRD-FR-004 -->PRD-FR-004：范围包括读取架构图开关、提供高压与低压排列组合页签，以及按勾选组合生成逻辑设计表，构成连续业务链。原文未明确本期排除项，未提及不等于排除。（REQ-2026-001/FR-4）<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section scenarios -->
# 用户与场景
<!-- prd:item PRD-SCN-001 -->PRD-SCN-001：工程师在架构仿真平台中针对架构图整理开关逻辑设计表。原文称当前平台只能对架构图做连通性仿真，该现状未经过技术核验。（REQ-2026-001/SCN-1）<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section functional_requirements -->
# 功能需求
| 编号 | 内容 | 分析来源 |
| --- | --- | --- |
| <!-- prd:item PRD-FR-001 -->PRD-FR-001 | 读取架构图中的开关，分为高压开关组合和低压开关组合；分类依据尚未说明。 | REQ-2026-001/FR-1<!-- /prd:item --> |
| <!-- prd:item PRD-FR-002 -->PRD-FR-002 | 高压开关作为高压排列组合tab，低压开关作为低压排列组合tab。 | REQ-2026-001/FR-2<!-- /prd:item --> |
| <!-- prd:item PRD-FR-003 -->PRD-FR-003 | 根据勾选的高低压组合生成逻辑设计表；组合含义、两类选中项如何决定输出及表格内容尚未定义。 | REQ-2026-001/FR-3<!-- /prd:item --> |
<!-- /prd:section -->

<!-- prd:section business_rules -->
# 业务规则
分析结果中无此项。组合语义、合法性和输出规则尚待确认，不能据空列表认定不存在约束。
<!-- /prd:section -->

<!-- prd:section flows_states -->
# 流程与状态
<!-- prd:item PRD-FLOW-001 -->PRD-FLOW-001：【推断】【待确认】候选流程为读取架构图开关并区分高低压，在对应tab形成可选组合，工程师勾选后生成逻辑设计表。组合形成、跨压配合和输出判定尚未确认，这不是完整可执行流程。（REQ-2026-001/FLOW-1）<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section boundaries_exceptions -->
# 边界与异常
<!-- prd:item PRD-BND-001 -->PRD-BND-001：【推断】需区分图中无开关、仅有一类开关、两类均未勾选和仅勾选一类；是否阻止生成、生成单类表或如何表示缺失侧均未确定。（REQ-2026-001/BND-1）<!-- /prd:item -->

<!-- prd:item PRD-BND-002 -->PRD-BND-002：【推断】若组合随开关数量、允许状态或动作增加而增长，或需跨压交叉，生成、展示、勾选和结果完整性可能受影响。算法、规模及处理方式未确认，不预设上限或截断策略。（REQ-2026-001/BND-2）<!-- /prd:item -->

<!-- prd:item PRD-EXC-001 -->PRD-EXC-001：【推断】若存在不允许的状态、互斥或动作先后约束，可能有不合法组合；约束是否存在以及隐藏、禁选或标记等处理方式均待业务定义。（REQ-2026-001/EXC-1）<!-- /prd:item -->
<!-- /prd:section -->

<!-- prd:section acceptance_criteria -->
# 验收条件
| 编号 | 内容 | 分析来源 |
| --- | --- | --- |
| <!-- prd:item PRD-AC-001 -->PRD-AC-001 | 界面分别提供与高压、低压开关类别对应的排列组合tab；只验证页签职责，不代表页签内部生成规则已明确。 | REQ-2026-001/AC-1<!-- /prd:item --> |
| <!-- prd:item PRD-AC-002 -->PRD-AC-002 | 【推断】【待确认】业务确认组合语义和合法输入后，使用已知架构图与明确勾选项核对输出行集合、开关对应关系及单元格含义；空输入需有可判定结果。目前没有正确结果样例，不构成完整核心验收。 | REQ-2026-001/AC-2<!-- /prd:item --> |
<!-- /prd:section -->

<!-- prd:section ux -->
# 界面与交互
依赖高低压排列组合tab与勾选交互。原文未提供现有页面资料；入口、生成触发方式、未选状态、组合展示及表格布局尚未确定。相关设计待业务规则确认后开展。（REQ-2026-001/FR-2、REQ-2026-001/FR-3；/ux_assessment/design_pending_items/0）
<!-- /prd:section -->

<!-- prd:section technical -->
# 研发确认项
未开展技术可行性评估；请研发核实开关标识、高低压分类、状态或动作数据以及组合生成和展示能力、限制。（REQ-2026-001/Q-7）
<!-- /prd:section -->

<!-- prd:section residuals -->
# 遗留事项
以下推荐仅为讨论方向，均未被用户采纳。

<!-- prd:residual REQ-2026-001/Q-1 -->REQ-2026-001/Q-1（P0，open，ask_product）：组合是状态配置、动作顺序、预定义方案还是其他？推荐以状态配置为讨论起点，不代表二态或全部合法；关注顺序则考虑动作顺序。已在第1轮提出，尚未回答。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/Q-2 -->REQ-2026-001/Q-2（P0，open，ask_product）：高低压选中项如何共同决定结果？可讨论交叉、指定配对或分别生成；若须覆盖所有搭配可考虑交叉，若只允许特定搭配可考虑指定配对，均未确认。已在第1轮提出。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/Q-3 -->REQ-2026-001/Q-3（P0，open，ask_product）：表格行、列、单元格表达什么？静态组合可讨论按组合和开关组织，动作顺序可讨论按步骤组织；有现成模板则优先提供模板或期望样例。已在第1轮提出。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/Q-4 -->REQ-2026-001/Q-4（P0，open，ask_business）：组合语义确定后，业务需提供可用状态或动作及合法性约束依据；不能默认两态或互锁。仅登记，尚未提出。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/Q-5 -->REQ-2026-001/Q-5（P0，open，ask_product）：无开关、仅有一类、均未勾选或仅勾选一类时应如何处理？建议区分不存在与主动未选，再结合跨压语义确定。仅登记，尚未提出。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/Q-6 -->REQ-2026-001/Q-6（P1，open，ask_product）：规模增长导致展示、选择或生成困难时如何处理？可讨论先告知规模、确认继续或缩小选择，须经研发验证和用户确认；不静默截断、不承诺规模或耗时。仅登记，尚未提出。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/Q-7 -->REQ-2026-001/Q-7（P1，open，ask_dev）：研发结合数据模型、接口及可复现示例核实读取、分类、状态或动作数据和组合能力及限制，记录证据；没有资料则保持待确认。研发核实不代替业务定义。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/GAP-1 -->REQ-2026-001/GAP-1：【推断】排列组合含义及合法状态、约束未定义；不能据此认定二态全排列或特定互锁。关联 Q-1、Q-4。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/GAP-2 -->REQ-2026-001/GAP-2：【推断】两类勾选项与结果的关系未定义，不能默认交叉、一一配对或独立输出。关联 Q-2。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/GAP-3 -->REQ-2026-001/GAP-3：【推断】缺表结构、单元格含义及正确样例；不能从现有连通性仿真推断本需求必须运行仿真或输出仿真结论。关联 Q-3、AC-2。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/GAP-4 -->REQ-2026-001/GAP-4：【推断】缺平台数据模型、接口及分类资料，读取能力、分类属性和状态数据未经技术核实。关联 Q-7。<!-- /prd:residual -->

<!-- prd:residual REQ-2026-001/FLOW-1 -->REQ-2026-001/FLOW-1：【推断】【待确认】候选流程的组合形成、跨压配合和输出判定需验证。<!-- /prd:residual -->
<!-- prd:residual REQ-2026-001/BND-1 -->REQ-2026-001/BND-1：【推断】空图、单类和未选等边界的行为待验证，见 Q-5。<!-- /prd:residual -->
<!-- prd:residual REQ-2026-001/BND-2 -->REQ-2026-001/BND-2：【推断】条件性规模风险及处理待验证，见 Q-6、Q-7。<!-- /prd:residual -->
<!-- prd:residual REQ-2026-001/EXC-1 -->REQ-2026-001/EXC-1：【推断】不合法组合是否存在及其处理待业务验证，见 Q-4。<!-- /prd:residual -->
<!-- prd:residual REQ-2026-001/AC-2 -->REQ-2026-001/AC-2：【推断】【待确认】核心验收依赖组合、合法输入、输出及边界预期，尚不能判定。<!-- /prd:residual -->
<!-- prd:residual /ux_assessment/design_pending_items/0 -->/ux_assessment/design_pending_items/0：缺现有页面和交互资料，业务组合与输出规则确认后再确定展示、选择反馈及表格布局。<!-- /prd:residual -->
<!-- /prd:section -->

<!-- prd:section appendix -->
# 附录
领域术语：架构图、高压开关、低压开关、高压排列组合tab、低压排列组合tab、逻辑设计表、连通性仿真。业务来源 SRC-1：《高低压开关组合逻辑设计表原始需求》；正文中的分析引用可追溯至该来源及具体位置。未开展历史需求检索或基线对照，不声称与旧规则兼容或历史无冲突。
<!-- /prd:section -->
