# 简化交接草稿（非完整 PRD）

    UX-MISSING（合成体验分析）

需求：UX-MISSING；基于分析修订：1
analysis_status=clarifying；readiness=not_ready
待产品负责人确认；本工具不分配正式 PRD 编号、不发布。

> 风险：仅为初步草稿，存在未解决缺口，不能作为已就绪需求交付。

## 分析条目摘录与映射

以下编号仅用于分析追溯，不是正式 PRD 需求编号。

### requirements.goals

映射：UX-MISSING/GOAL-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    合成体验能力验证：按本例实际资料范围分析，不把设计建议当既有界面

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases.json：UX-MISSING"
        }
      ],
      "related_ids": []
    }

### requirements.scenarios

映射：UX-MISSING/SCN-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    建议：多角色采购审批工作台作为待设计界面；入口、页面拆分和现有页面情况均未确认。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases[0].requirement"
        }
      ],
      "related_ids": []
    }

### requirements.functional_requirements

映射：UX-MISSING/FR-1 | tag=confirmed | status=active | 当前条目

    新增多角色采购审批工作台，支持审批人分配、驳回修改后重提和批量处理。没有视觉稿、现有页面截图、流程图或设计规范；角色范围、混合批次规则和重提状态也未定。先判断需要哪些类型的资料并登记待设计事项，不自行设计完整界面。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases.json：UX-MISSING"
        }
      ],
      "related_ids": []
    }

## 体验与待设计事项

保留实际界面依赖判断、设计待办及候选流程；视觉建议不是已确认界面或已实现行为。

    {
      "ui_dependent": true,
      "design_pending_items": [
        "待补角色及职责资料、审批流程和状态转换说明；建议用角色泳道与状态图表达，不要求高保真。",
        "待设计审批人分配、驳回修改后重提、批量处理以及各操作结果的界面与状态；业务规则确定前不细化完整界面。"
      ],
      "visual_recommendations": [
        "建议提供现有页面截图或设计规范（如有），以及能表达关键流程和状态的低保真参考；当前无视觉资料，无法评价现有布局或交互。"
      ],
      "interaction_flows": [
        "建议、待确认：角色进入工作台，分配审批人或处理申请；驳回后由相关角色修改并重提，批量处理按待定规则反馈逐项结果。角色交接与状态变化尚未确定。"
      ]
    }

## 遗留事项与问题记录

open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。

映射：UX-MISSING/Q-1 | P0 | open | ask_product

    {
      "question": "哪些角色参与审批人分配、审批、驳回后的修改和重提，各自的权限与交接边界是什么？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "角色范围和职责未定。",
      "impact": "无法确定授权操作或还原核心审批流程。",
      "options": [
        "由产品逐角色指定权限和交接",
        "限定少量角色参与并明确职责",
        "其他或暂不确定"
      ],
      "recommendation": "建议先按操作列出角色权限和交接，再设计页面；尚未确认。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-1"
    }

映射：UX-MISSING/Q-2 | P0 | open | ask_product

    {
      "question": "批量中包含状态或权限不一致的申请时如何处理？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "混合批次规则未定。",
      "impact": "影响实际处理对象、部分结果和验收。",
      "options": [
        "逐条判断并反馈结果",
        "整批拒绝",
        "其他或暂不确定"
      ],
      "recommendation": "建议评估逐条判断与逐项反馈，具体由产品确认。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-2"
    }

映射：UX-MISSING/Q-3 | P0 | open | ask_product

    {
      "question": "驳回后修改和重提如何改变状态，以及重提后如何重新分配审批？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "重提状态及后续流转未定。",
      "impact": "影响申请生命周期和审批责任。",
      "options": [
        "重提后回到待审批并按既定规则分配",
        "重提后先重新分配审批人",
        "其他或暂不确定"
      ],
      "recommendation": "建议先明确状态转换和审批责任，再制作对应交互。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-3"
    }

映射：UX-MISSING/Q-4 | P1 | open | ask_design

    {
      "question": "业务规则确定后，工作台的关键状态和操作反馈如何呈现？",
      "priority": "P1",
      "resolution": "ask_design",
      "reason": "未提供视觉稿或流程图。",
      "impact": "影响操作可理解性和设计交接。",
      "options": [
        "提供流程图与低保真状态稿",
        "先提供文字交互说明",
        "其他或暂不确定"
      ],
      "recommendation": "建议先用流程与关键状态低保真说明，避免过早制作高保真。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-4"
    }

映射：UX-MISSING/Q-5 | P1 | open | ask_dev

    {
      "question": "现有系统是否具备审批分配、重提和逐项批处理所需的接口与状态能力？",
      "priority": "P1",
      "resolution": "ask_dev",
      "reason": "没有现有架构或接口证据。",
      "impact": "影响实现方案和工作量，当前技术可行性未知。",
      "options": [
        "核查现有能力并提供接口与状态说明",
        "评估需要新增的能力",
        "其他或暂不确定"
      ],
      "recommendation": "建议研发依据现有实现核实，不预设能力存在。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-5"
    }

完成清单第 4 项未满足：
    实际模型登记的核心规则/设计待决事项未答，保留缺口

完成清单第 7 项未满足：
    实际模型登记的核心规则/设计待决事项未答，保留缺口

完成清单第 11 项未满足：
    实际模型登记的核心规则/设计待决事项未答，保留缺口

