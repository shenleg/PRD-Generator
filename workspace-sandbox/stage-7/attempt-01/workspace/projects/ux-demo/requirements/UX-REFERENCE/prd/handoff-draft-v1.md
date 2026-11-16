# 简化交接草稿（非完整 PRD）

    UX-REFERENCE（合成体验分析）

需求：UX-REFERENCE；基于分析修订：1
analysis_status=clarifying；readiness=not_ready
待产品负责人确认；本工具不分配正式 PRD 编号、不发布。

> 风险：仅为初步草稿，存在未解决缺口，不能作为已就绪需求交付。

## 分析条目摘录与映射

以下编号仅用于分析追溯，不是正式 PRD 需求编号。

### requirements.goals

映射：UX-REFERENCE/GOAL-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    合成体验能力验证：按本例实际资料范围分析，不把设计建议当既有界面

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases.json：UX-REFERENCE"
        }
      ],
      "related_ids": []
    }

### requirements.scenarios

映射：UX-REFERENCE/SCN-1 | tag=confirmed | status=active | 当前条目

    合成参考中的申请列表常态页面；仅证明截图中的展示。

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

映射：UX-REFERENCE/SCN-2 | tag=inferred | status=active | 当前条目；推断，未经确认

    建议在列表设计批量撤回入口及选择、处理和结果状态；具体载体待设计，并非已存在功能。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases[2].requirement"
        }
      ],
      "related_ids": []
    }

### requirements.functional_requirements

映射：UX-REFERENCE/FR-1 | tag=confirmed | status=active | 当前条目

    基于提供的列表参考，为员工增加批量撤回入口。仅允许创建人撤自己的待审批申请，其他申请不得改变；逐条处理，成功和失败需清晰反馈。具体选择范围、跨页行为、重复提交和执行时状态变化结果尚未决定。说明截图已有什么、需要补哪些交互和状态，不把设计建议当现有功能。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases.json：UX-REFERENCE"
        }
      ],
      "related_ids": []
    }

### business_assessment.boundaries

映射：UX-REFERENCE/BND-1 | tag=confirmed | status=active | 当前条目

    顶部显示“采购工作台”和“当前用户：员工甲”；左侧“申请列表”处于高亮。

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

映射：UX-REFERENCE/BND-2 | tag=confirmed | status=active | 当前条目

    主区显示“申请列表”和“新建申请”；筛选区显示申请状态、关键词、查询和重置。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-2",
          "location": "主区标题及其下方筛选区"
        }
      ],
      "related_ids": []
    }

映射：UX-REFERENCE/BND-3 | tag=confirmed | status=active | 当前条目

    表格列为申请编号、申请人、申请状态、申请金额、操作；四行分别包含员工甲和员工乙，以及待审批、已通过、已取消状态，每行显示“查看”。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-2",
          "location": "列表表头及四条示意数据"
        }
      ],
      "related_ids": []
    }

映射：UX-REFERENCE/BND-4 | tag=confirmed | status=active | 当前条目

    列表底部显示“示意数据：4条”和“第1页”；该常态截图未见批量选择控件或批量撤回入口。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-2",
          "location": "列表区域及底部"
        }
      ],
      "related_ids": []
    }

映射：UX-REFERENCE/BND-5 | tag=confirmed | status=active | 当前条目

    截图底部文字注明只展示列表常态，未提供选中态、确认弹窗、加载/空数据/错误画面，也不说明后台权限与状态规则。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-2",
          "location": "页面底部说明条"
        }
      ],
      "related_ids": []
    }

## 体验与待设计事项

保留实际界面依赖判断、设计待办及候选流程；视觉建议不是已确认界面或已实现行为。

    {
      "ui_dependent": true,
      "design_pending_items": [
        "待设计可选与不可选项的区分、选择范围、入口和逐条结果反馈；不得以截图中的申请人和状态推断实际授权。",
        "待设计选中、执行中、全部成功、部分失败和错误等状态；跨页与重复提交的呈现须以产品规则为前提。"
      ],
      "visual_recommendations": [
        "建议沿用截图作为列表常态的低保真构图参考，补充选择、执行和结果的低保真状态及文字交互说明；截图不证明真实系统或点击行为。",
        "建议用明确文字区分成功、失败及原因，避免仅靠颜色表达结果；具体呈现待设计确认。"
      ],
      "interaction_flows": [
        "已明确业务约束：仅创建人可撤回自己的待审批申请，其他申请不得改变；逐条处理并清晰反馈成功和失败。",
        "建议、待确认：在列表选取申请并发起批量撤回，逐项校验与处理后展示结果；选择范围、跨页、重复提交及执行时状态变化均待产品确定。"
      ]
    }

## 遗留事项与问题记录

open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。

映射：UX-REFERENCE/Q-1 | P0 | open | ask_product

    {
      "question": "批量选择允许覆盖哪些记录，筛选变化或跨页时选择范围如何计算？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "选择范围及跨页行为尚未决定。",
      "impact": "直接决定实际处理对象，可能造成误操作或遗漏。",
      "options": [
        "仅允许选择当前页",
        "允许跨页保留明确选择",
        "允许选择全部筛选结果",
        "其他或暂不确定"
      ],
      "recommendation": "建议先采用范围清晰的选择方案并明确展示对象数量，待产品确认。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-1"
    }

映射：UX-REFERENCE/Q-2 | P0 | open | ask_product

    {
      "question": "对同一批次重复提交时应如何处理？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "重复提交规则未定。",
      "impact": "影响是否重复执行及结果可验收性。",
      "options": [
        "阻止重复提交",
        "允许提交但保证已处理项不重复生效",
        "其他或暂不确定"
      ],
      "recommendation": "建议优先避免重复生效，并明确重复请求的反馈；具体规则待确认。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-2"
    }

映射：UX-REFERENCE/Q-3 | P0 | open | ask_product

    {
      "question": "执行时申请不再处于待审批或创建人资格不满足时，该项如何反馈？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "执行时状态变化结果尚未决定，但其他申请不得改变。",
      "impact": "影响逐条处理结果及权限边界验收。",
      "options": [
        "跳过该项并反馈原因",
        "停止后续处理并反馈已有结果",
        "其他或暂不确定"
      ],
      "recommendation": "建议在执行时重新校验且不改变不符合条件的申请，失败反馈方式待产品确认。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-3"
    }

映射：UX-REFERENCE/Q-4 | P1 | open | ask_design

    {
      "question": "选择与逐项反馈应如何呈现？",
      "priority": "P1",
      "resolution": "ask_design",
      "reason": "参考仅有常态列表，缺少交互状态。",
      "impact": "影响操作可理解性。",
      "options": [
        "补充低保真关键状态",
        "补充文字交互规格",
        "其他或暂不确定"
      ],
      "recommendation": "建议先依据确认后的规则补充关键状态。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-4"
    }

映射：UX-REFERENCE/Q-5 | P1 | open | ask_dev

    {
      "question": "现有接口是否支持逐项权限及状态校验、重复请求控制和逐项结果？",
      "priority": "P1",
      "resolution": "ask_dev",
      "reason": "截图和说明没有后台实现证据。",
      "impact": "影响方案及实现工作量，技术能力未知。",
      "options": [
        "核查现有接口",
        "评估新增或调整接口",
        "其他或暂不确定"
      ],
      "recommendation": "建议研发逐项核实，不能由截图推断。",
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

