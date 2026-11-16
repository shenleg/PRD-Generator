# 简化交接草稿（非完整 PRD）

    架构图高低压开关组合逻辑设计表

需求：REQ-2026-001；基于分析修订：4
analysis_status=completed；readiness=not_ready
待产品负责人确认；本工具不分配正式 PRD 编号、不发布。

> 风险：仅为初步草稿，存在未解决缺口，不能作为已就绪需求交付。

## 分析条目摘录与映射

以下编号仅用于分析追溯，不是正式 PRD 需求编号。

### requirements.goals

映射：REQ-2026-001/GOAL-1 | tag=confirmed | status=active | 当前条目

    在架构仿真平台的架构图中增加高低压开关组合逻辑设计表，改善工程师手工整理开关动作逻辑设计表效率低、容易出错的问题；原文未给出量化收益指标。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第1—2行：需求标题、背景"
        }
      ]
    }

### requirements.scenarios

映射：REQ-2026-001/SCN-1 | tag=confirmed | status=active | 当前条目

    工程师在架构仿真平台中针对架构图的开关整理逻辑设计表；平台当前只能对架构图做连通性仿真，原文要求新增按勾选的高低压组合生成逻辑设计表的场景。当前平台能力仅为原文陈述，未做技术核验。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第2、4—6行：背景、开关读取、页签及生成设计表"
        }
      ],
      "related_ids": [
        "GOAL-1"
      ]
    }

### requirements.functional_requirements

映射：REQ-2026-001/FR-1 | tag=confirmed | status=active | 当前条目

    读取架构图中的开关，分为高压开关组合和低压开关组合；原文未说明高低压分类依据。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第4行：读取图中开关，分为高低压开关组合"
        }
      ],
      "related_ids": [
        "SCN-1"
      ]
    }

映射：REQ-2026-001/FR-2 | tag=confirmed | status=active | 当前条目

    高压开关作为高压排列组合tab，低压开关作为低压排列组合tab。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5行：高压、低压排列组合tab"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

映射：REQ-2026-001/FR-3 | tag=confirmed | status=active | 当前条目

    逻辑设计根据勾选的高低压组合生成逻辑设计表；原文未定义组合的含义、高低压选中项如何共同决定输出以及表格内容。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第6行：根据勾选的高低压组合生成逻辑设计表"
        }
      ],
      "related_ids": [
        "FR-2",
        "GOAL-1"
      ]
    }

### requirements.acceptance_criteria

映射：REQ-2026-001/AC-1 | tag=confirmed | status=active | 当前条目

    界面应分别提供高压排列组合tab和低压排列组合tab，与原文规定的高低压开关类别对应；该条仅验证页签职责，不代表页签内的组合生成规则已明确。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5行：两个排列组合tab"
        }
      ],
      "related_ids": [
        "FR-2"
      ]
    }

映射：REQ-2026-001/AC-2 | tag=inferred | status=to_reassess | 待重评，非确定内容；推断，未经确认

    验收草案：在业务确认组合语义及合法输入后，用已知架构图、明确的高低压勾选项验证输出行集合、开关对应关系与单元格含义；空输入须有可判定结果。由于这些预期尚未提供，当前不能给出正确结果样例，不构成完整核心验收。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第4—6行：开关组合及设计表生成要求"
        }
      ],
      "related_ids": [
        "FR-3",
        "Q-1",
        "Q-4",
        "Q-2",
        "Q-3",
        "Q-5"
      ]
    }

### requirements.scope.in_scope

映射：REQ-2026-001/FR-4 | tag=confirmed | status=active | 当前条目

    本次明确包含：读取架构图开关、提供高压与低压排列组合页签、根据勾选的高低压组合生成逻辑设计表。这些构成一个连续业务链；原文未明确本期排除项，不能把未提及的功能视为已被排除。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第4—6行：本次功能范围"
        }
      ],
      "related_ids": [
        "FR-1",
        "FR-2",
        "FR-3"
      ]
    }

### business_assessment.flows

映射：REQ-2026-001/FLOW-1 | tag=inferred | status=to_reassess | 待重评，非确定内容；推断，未经确认

    候选主流程：读取架构图开关并区分高低压→在对应tab形成可选组合→工程师勾选组合→生成逻辑设计表。此为依照原文串联的流程草案；组合形成规则、跨压配合方式及输出判定未确认，尚不能还原可执行的完整流程。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第4—6行：读取、页签、勾选与生成"
        }
      ],
      "related_ids": [
        "FR-1",
        "FR-2",
        "FR-3",
        "Q-1",
        "Q-2",
        "Q-3"
      ]
    }

### business_assessment.boundaries

映射：REQ-2026-001/BND-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    候选边界：图中没有开关、仅有高压或仅有低压开关，以及存在开关但两类均未勾选或只勾选一类。各情形应禁止生成、生成单类表或如何表示缺失侧尚未确定，不能把无开关和未勾选当作同一状态。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第4—6行：图中开关、高低压分类及勾选生成"
        }
      ],
      "related_ids": [
        "FR-1",
        "FR-3",
        "Q-5"
      ]
    }

映射：REQ-2026-001/BND-2 | tag=inferred | status=active | 当前条目；推断，未经确认

    条件性规模边界：若组合数量随开关数量或允许状态、动作的增加而增长，或高低压勾选项需要交叉组合，则生成、展示、勾选及结果完整性可能受影响。尚未确认组合算法、实际规模和业务可接受的处理方式；不假设二态全排列、具体数量上限、分页或截断策略。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第4—6行：高低压排列组合及勾选生成"
        }
      ],
      "related_ids": [
        "FR-2",
        "FR-3",
        "Q-6",
        "Q-7"
      ]
    }

### business_assessment.exceptions

映射：REQ-2026-001/EXC-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    候选异常：若开关存在不允许的状态、组合互斥或动作先后约束，组合可能不合法；是否确有这些约束及不合法组合应隐藏、禁选还是保留标记均待业务定义。不据行业常识编造具体电气互锁规则。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第2、4—6行：开关动作、排列组合及生成设计表"
        }
      ],
      "related_ids": [
        "FR-2",
        "FR-3",
        "Q-4"
      ]
    }

### business_assessment.gaps

映射：REQ-2026-001/GAP-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    “排列组合”未说明是开关状态赋值、动作顺序还是预定义方案；不能据此认定每个开关只有两态、执行全排列或存在特定互锁。合法状态及组合约束也尚未给出。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第2、4—5行：开关动作、开关组合、排列组合tab"
        }
      ],
      "related_ids": [
        "FR-2",
        "Q-1",
        "Q-4"
      ]
    }

映射：REQ-2026-001/GAP-2 | tag=inferred | status=active | 当前条目；推断，未经确认

    原文没有定义两个tab中勾选项如何决定最终设计表，不能默认跨压做笛卡尔积，也不能默认一一配对或各自独立输出。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5—6行：两个tab及根据勾选的高低压组合生成"
        }
      ],
      "related_ids": [
        "FR-3",
        "Q-2"
      ]
    }

映射：REQ-2026-001/GAP-3 | tag=inferred | status=active | 当前条目；推断，未经确认

    逻辑设计表的行列结构、单元格含义及可用来判定正确性的输出样例均未提供；不能凭“连通性仿真”推断本次必须运行仿真或输出仿真结论。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第2、6行：现有仿真能力与设计表生成诉求"
        }
      ],
      "related_ids": [
        "FR-3",
        "Q-3",
        "AC-2"
      ]
    }

映射：REQ-2026-001/GAP-4 | tag=inferred | status=active | 当前条目；推断，未经确认

    本轮仅取得业务原文，没有现有平台的数据模型、接口或开关分类资料；读取能力、高低压属性及支持的状态数据尚未技术核实。现有平台能力须由研发确认，不能要求产品承诺实现机制。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第2、4行：平台现状及读取图中开关"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-7"
      ]
    }

### assumptions

映射：REQ-2026-001/ASM-1 | tag=assumption | status=active | 当前条目；暂定假设，待验证

    若组合规模影响一次展示、选择或生成，暂以告知预计规模、由工程师确认继续或缩小选择范围作为待验证的业务处理方向，不静默截断结果。预计规模是否可取得以及继续生成的实际能力仍待研发确认；不设定具体数量或耗时，不承诺现有平台已支持此方向。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第4—6行：高低压排列组合及勾选生成；原文仅触发规模增长边界，本处理方向不是原文规则"
        }
      ],
      "basis": "第1轮业务追问已经达到调用方配置的1轮上限。按question-strategy.md的达到上限规则，将可合理推荐的产品P1 Q-6暂按既有推荐登记，以明确结果完整性及规模反馈方向；这是分析流程采用的暂定假设，不是用户选择“暂不确定”，也不是用户已确认的产品决策。组合定义等P0不受此假设替代。",
      "verification": "由产品负责人或用户在后续明确确认时，结合实际架构图及组合规模样例验证“告知规模、确认继续或缩小范围”的业务预期；研发通过现有数据与可复现实验核实规模估计及处理能力，并通过Q-7回填证据。未经这些验证，不把此假设视为已确认规则或技术能力。",
      "related_question": "Q-6",
      "related_ids": [
        "BND-2",
        "FR-2",
        "FR-3",
        "Q-7"
      ]
    }

## 遗留事项与问题记录

open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。

映射：REQ-2026-001/Q-1 | P0 | open | ask_product

    {
      "question": "这里一个“开关组合”的业务含义是什么？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "这是组合生成的前置定义；原文同时出现开关动作和排列组合，不能自行解释成开/关二态全排列。本轮第1轮实际提出。",
      "impact": "决定tab中的候选项是什么，以及后续组合与设计表应表达状态还是动作。",
      "options": [
        "A. 一组开关各自所处状态的一种配置，不考虑动作顺序",
        "B. 多个开关动作的先后顺序，顺序不同即不同组合",
        "C. 业务预先定义的一套开关方案，不穷举所有配置或顺序",
        "D. 其他，请说明",
        "E. 暂不确定"
      ],
      "recommendation": "若目标是比较不同开关配置，推荐A作为讨论起点，先明确每个组合表示什么；A并不意味着每个开关只有两态，也不意味着所有配置都合法。若关心操作先后，应选B。用户选择前不采用任何解释。",
      "status": "open",
      "related_ids": [
        "FR-2",
        "GAP-1",
        "FLOW-1",
        "AC-2"
      ],
      "asked_round": 1,
      "id": "Q-1"
    }

映射：REQ-2026-001/Q-2 | P0 | open | ask_product

    {
      "question": "两个tab里勾选的高压组合与低压组合，怎样共同决定要生成的结果？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "仅有“根据勾选的高低压组合”不足以判断最终结果集合；不能默认跨压组合方式。本轮第1轮实际提出。",
      "impact": "不同规则会产生不同输出条目，错误理解会造成漏生成或多生成，核心生成逻辑无法验收。",
      "options": [
        "A. 每个选中高压组合与每个选中低压组合交叉配合",
        "B. 由工程师明确指定高低压组合配对，只生成指定配对",
        "C. 两类分别生成各自的结果，不做跨压配合",
        "D. 其他，请说明",
        "E. 暂不确定"
      ],
      "recommendation": "若设计表需要覆盖选中范围内的所有高低压搭配，推荐A，覆盖关系明确；若只允许特定业务搭配，B更合适。该推荐不是已确认的笛卡尔积规则。",
      "status": "open",
      "related_ids": [
        "FR-3",
        "GAP-2",
        "FLOW-1",
        "AC-2"
      ],
      "asked_round": 1,
      "id": "Q-2"
    }

映射：REQ-2026-001/Q-3 | P0 | open | ask_product

    {
      "question": "生成的逻辑设计表，行、列与单元格分别应表达什么？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "原文只命名了输出，未给表结构或正确结果样例；这是核心输出契约而非视觉细节。本轮第1轮实际提出。",
      "impact": "无法仅凭生成了一个表判断功能正确，也无法确定是否要求动作过程或其他结果信息。",
      "options": [
        "A. 每行一个最终开关组合，每列一个开关，单元格记录该组合中该开关的状态",
        "B. 按动作步骤逐行记录，展示操作对象及动作前后状态",
        "C. 按已有业务模板输出，请提供模板或一份期望结果样例",
        "D. 其他，请说明",
        "E. 暂不确定"
      ],
      "recommendation": "若前面选择静态状态组合，推荐A作为最小可核对表结构，便于逐个组合检查开关状态；若选择动作顺序，B更匹配。若已有固定模板则优先C，不能自行发明模板字段。",
      "status": "open",
      "related_ids": [
        "FR-3",
        "GAP-3",
        "AC-2"
      ],
      "asked_round": 1,
      "id": "Q-3"
    }

映射：REQ-2026-001/Q-4 | P0 | open | ask_business

    {
      "question": "在确认组合含义后，哪些开关状态或动作可用，哪些组合属于不合法输入？",
      "priority": "P0",
      "resolution": "ask_business",
      "reason": "原文未定义合法输入集合。此项依赖组合语义，先登记，未在本轮向用户提出。",
      "impact": "不能确定候选组合是否完整、是否含有不应使用的组合，以及非法输入的预期处理。",
      "options": [],
      "recommendation": "先由业务提供可用状态或动作及约束依据；没有依据时不默认两态、不编造互锁，也不宣布全部配置合法。",
      "status": "open",
      "related_ids": [
        "GAP-1",
        "EXC-1",
        "Q-1",
        "AC-2"
      ],
      "id": "Q-4"
    }

映射：REQ-2026-001/Q-5 | P0 | open | ask_product

    {
      "question": "图中无开关、仅存在一类开关，以及两类均未勾选或仅勾选一类时，生成动作应有什么可判定结果？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "这些是由读图和按勾选项生成直接引出的关键输入边界，规则尚未给出。仅登记，不占本轮已提出的三个问题；后续若追问应按独立边界决策组织。",
      "impact": "不能判定空输入和单类输入应允许生成、阻止生成还是产生何种结果，核心边界验收仍不完整。",
      "options": [],
      "recommendation": "先区分图中不存在该类开关与工程师主动不勾选，再结合已确认的跨压组合语义确定预期；当前不采用任何空输入策略。",
      "status": "open",
      "related_ids": [
        "BND-1",
        "FR-3",
        "AC-2",
        "Q-2"
      ],
      "id": "Q-5"
    }

映射：REQ-2026-001/Q-6 | P1 | provisional | ask_product

    {
      "question": "若候选或选中组合随规模增长而难以一次展示、选择或生成，业务希望怎样处理？",
      "priority": "P1",
      "resolution": "ask_product",
      "reason": "业务追问达到配置上限1轮，依上限处理规则采用此前可合理推荐的规模处理方向，已有active ASM记录依据和验证责任。此状态不是因为用户选择“暂不确定”；实际回复仅为“这轮先不回答。”，没有业务确认或风险接受。未向用户追加本题，原问题不计入已发出的业务追问。",
      "impact": "会影响完整性、等待体验及是否允许缩小选择范围；不能静默截断结果。",
      "options": [],
      "recommendation": "候选方向是先告知预计规模，由工程师确认继续或缩小选择，避免静默漏项；需要结合研发的实际能力验证，由用户确认后才可采用，不自行承诺规模或耗时。",
      "status": "provisional",
      "related_ids": [
        "BND-2",
        "Q-7",
        "FR-2",
        "FR-3",
        "ASM-1"
      ],
      "id": "Q-6"
    }

映射：REQ-2026-001/Q-7 | P1 | open | ask_dev

    {
      "question": "请研发核实当前平台可读取的开关标识、高低压分类及状态/动作数据，以及组合生成和展示的现有能力与限制。",
      "priority": "P1",
      "resolution": "ask_dev",
      "reason": "业务原文不是实现能力证据，本阶段不开展技术评估。研发待确认登记，不要求产品当轮回答，也不占业务追问额度。",
      "impact": "影响后续数据映射、实现方案及规模风险评估；不能据此给出确定可行结论，也不能由研发替代业务定义组合与表格预期。",
      "options": [],
      "recommendation": "由研发结合现有数据模型、接口资料及可复现示例核实，并记录证据；没有资料时保持待确认。",
      "status": "open",
      "related_ids": [
        "FR-1",
        "FR-2",
        "FR-3",
        "GAP-4",
        "BND-2"
      ],
      "id": "Q-7"
    }

完成清单第 3 项未满足：
    组合定义、跨压配合与输出契约仍未回答，核心流程不能完整还原；结束仅停止追问，不补全规则。

完成清单第 4 项未满足：
    组合语义、合法状态和约束及高低压选中项关系仍未知，对应P0保持open；未把结束视为采用推荐。

完成清单第 6 项未满足：
    无开关、单类开关、未勾选及不合法组合等关键边界和异常的处理仍未明确；ASM-1仅覆盖规模P1的暂定方向，不能代替这些P0。

完成清单第 7 项未满足：
    核心输出及边界仍没有可判定预期，AC-2继续to_reassess，不能形成完整可验证的核心验收。

