# 简化交接草稿（非完整 PRD）

    UX-STATES（合成体验分析）

需求：UX-STATES；基于分析修订：1
analysis_status=clarifying；readiness=not_ready
待产品负责人确认；本工具不分配正式 PRD 编号、不发布。

> 风险：仅为初步草稿，存在未解决缺口，不能作为已就绪需求交付。

## 分析条目摘录与映射

以下编号仅用于分析追溯，不是正式 PRD 需求编号。

### requirements.goals

映射：UX-STATES/GOAL-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    合成体验能力验证：按本例实际资料范围分析，不把设计建议当既有界面

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases.json：UX-STATES"
        }
      ],
      "related_ids": []
    }

### requirements.scenarios

映射：UX-STATES/SCN-1 | tag=confirmed | status=active | 当前条目

    合成参考中的申请列表常态页面。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-2",
          "location": "主内容区"
        }
      ],
      "related_ids": []
    }

映射：UX-STATES/SCN-2 | tag=inferred | status=active | 当前条目；推断，未经确认

    建议：补充列表上的批量操作与任务结果状态，可采用何种页面或面板尚待设计。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases[4].requirement"
        }
      ],
      "related_ids": []
    }

### requirements.functional_requirements

映射：UX-STATES/FR-1 | tag=confirmed | status=active | 当前条目

    为本列表增加异步批量撤回，业务明确执行中不能重复发起同一批，失败项要能查看原因。仅提供常态参考，没提供选中、提交中、完成、部分失败、超时或取消状态设计。产品尚未决定已执行部分后是否允许取消及如何处理已经成功的申请；不能只当作取消按钮样式问题。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases.json：UX-STATES"
        }
      ],
      "related_ids": []
    }

### business_assessment.boundaries

映射：UX-STATES/BND-1 | tag=confirmed | status=active | 当前条目

    顶部显示“采购工作台”和当前用户员工甲；左侧选中“申请列表”。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-2",
          "location": "顶部栏、左侧导航"
        }
      ],
      "related_ids": []
    }

映射：UX-STATES/BND-2 | tag=confirmed | status=active | 当前条目

    主区有申请列表标题、新建申请按钮，申请状态和关键词筛选，以及查询、重置控件。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-2",
          "location": "标题区与筛选区"
        }
      ],
      "related_ids": []
    }

映射：UX-STATES/BND-3 | tag=confirmed | status=active | 当前条目

    列表显示申请编号、申请人、申请状态、申请金额、操作列，四条示意记录的操作均为“查看”。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-2",
          "location": "列表表头和数据行"
        }
      ],
      "related_ids": []
    }

映射：UX-STATES/BND-4 | tag=confirmed | status=active | 当前条目

    截图为常态列表，未显示选中、执行中、完成、部分失败、超时或取消状态；页面底部注明未提供选中态、确认弹窗、加载、空数据或错误画面。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-2",
          "location": "列表及底部说明条"
        }
      ],
      "related_ids": []
    }

## 体验与待设计事项

保留实际界面依赖判断、设计待办及候选流程；视觉建议不是已确认界面或已实现行为。

    {
      "ui_dependent": true,
      "design_pending_items": [
        "待设计选中、提交中、执行中、完成、部分失败、超时及取消相关状态，并展示失败原因；截图不能证明这些状态已经存在。",
        "待设计同一批次执行中的重复发起限制和反馈；取消控制须以产品对已执行部分的决策为前提。"
      ],
      "visual_recommendations": [
        "建议提供异步任务状态转换说明及关键状态低保真，而不是仅提供常态图；明确区分执行中、结果未知及已完成。",
        "建议让失败原因可被查看，并在结果中区分成功与失败；具体布局待设计。"
      ],
      "interaction_flows": [
        "已明确：执行中不能重复发起同一批，失败项要能查看原因。",
        "建议、待确认：选取申请并提交异步批次，执行中显示进度或状态，结束后查看逐项结果和失败原因；超时、取消及已完成部分的处理规则待确认。"
      ]
    }

## 遗留事项与问题记录

open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。

映射：UX-STATES/Q-1 | P0 | open | ask_product

    {
      "question": "批次已执行一部分后是否允许取消，已成功的申请及尚未执行的申请分别如何处理？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "产品尚未决定取消及已成功部分的处理。",
      "impact": "决定业务数据是否保留、回退或继续处理，是核心业务决策而非按钮样式。",
      "options": [
        "允许取消剩余项，保留已成功项",
        "不允许执行中取消",
        "允许取消并按明确规则处理已成功项",
        "其他或暂不确定"
      ],
      "recommendation": "建议优先评估停止未执行项并保留已成功结果的可理解性和业务适用性，不预设采用。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-1"
    }

映射：UX-STATES/Q-2 | P0 | open | ask_product

    {
      "question": "如何判断两次发起属于同一批，以及结果未知或超时后何时可再次发起？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "已规定执行中不可重复发起同一批，但批次边界及超时处理未定义。",
      "impact": "无法判定重复限制，也可能导致重复执行或任务被误认为结束。",
      "options": [
        "按任务标识判定，结果未知时先查询任务状态",
        "按申请集合及业务规则判定",
        "其他或暂不确定"
      ],
      "recommendation": "建议先明确业务上的批次身份与超时后恢复规则，再由研发落实。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-2"
    }

映射：UX-STATES/Q-3 | P1 | open | ask_design

    {
      "question": "异步任务的执行、部分失败、超时与取消如何呈现？",
      "priority": "P1",
      "resolution": "ask_design",
      "reason": "仅有常态参考。",
      "impact": "影响用户识别任务进度、失败原因及可用操作。",
      "options": [
        "补充关键状态低保真和转换说明",
        "先提供状态文案及交互说明",
        "其他或暂不确定"
      ],
      "recommendation": "建议按确认后的业务状态提供最小必要状态稿。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-3"
    }

映射：UX-STATES/Q-4 | P1 | open | ask_dev

    {
      "question": "现有服务是否支持异步任务状态查询、逐项失败原因及同批次防重？",
      "priority": "P1",
      "resolution": "ask_dev",
      "reason": "参考不包含后台实现证据。",
      "impact": "影响技术方案和实现成本；能力未知。",
      "options": [
        "核查现有任务及接口能力",
        "评估新增机制",
        "其他或暂不确定"
      ],
      "recommendation": "建议研发核实任务状态和防重能力，不把截图当技术证明。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-4"
    }

完成清单第 4 项未满足：
    实际模型登记的核心规则/设计待决事项未答，保留缺口

完成清单第 7 项未满足：
    实际模型登记的核心规则/设计待决事项未答，保留缺口

完成清单第 11 项未满足：
    实际模型登记的核心规则/设计待决事项未答，保留缺口

