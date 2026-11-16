# 简化交接草稿（非完整 PRD）

    UX-DATA（合成体验分析）

需求：UX-DATA；基于分析修订：1
analysis_status=clarifying；readiness=not_ready
待产品负责人确认；本工具不分配正式 PRD 编号、不发布。

> 风险：仅为初步草稿，存在未解决缺口，不能作为已就绪需求交付。

## 分析条目摘录与映射

以下编号仅用于分析追溯，不是正式 PRD 需求编号。

### requirements.goals

映射：UX-DATA/GOAL-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    合成体验能力验证：按本例实际资料范围分析，不把设计建议当既有界面

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases.json：UX-DATA"
        }
      ],
      "related_ids": []
    }

### requirements.scenarios

映射：UX-DATA/SCN-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    建议：在采购申请数据展示页增加趋势统计与明细查看区域；具体页面结构及是否拆分待设计。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases[5].requirement"
        }
      ],
      "related_ids": []
    }

### requirements.functional_requirements

映射：UX-DATA/FR-1 | tag=confirmed | status=active | 当前条目

    希望在采购申请数据展示页增加按状态和部门筛选的趋势统计，并能查看明细。没有视觉稿和数据字典，统计指标/时间维度/刷新规则/异常数据处理都未定；不要自定具体图表和业务口径或强制制作高保真原型。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "cases.json：UX-DATA"
        }
      ],
      "related_ids": []
    }

## 体验与待设计事项

保留实际界面依赖判断、设计待办及候选流程；视觉建议不是已确认界面或已实现行为。

    {
      "ui_dependent": true,
      "design_pending_items": [
        "待补数据字典、指标定义、时间维度、刷新及异常数据规则；当前无视觉稿，不能判断既有页面。",
        "待设计状态和部门筛选、趋势展示及明细查看的关系，以及空数据、异常和加载状态；不预设图表类型。"
      ],
      "visual_recommendations": [
        "建议先用指标定义和数据样例澄清信息需求，再选择适当的数据展示形式并提供必要的低保真参考；不强制高保真或指定图表。"
      ],
      "interaction_flows": [
        "建议、待确认：用户按状态和部门筛选，查看趋势统计并进入或展开相应明细；统计口径、时间和筛选与明细的联动规则尚未确定。"
      ]
    }

## 遗留事项与问题记录

open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。

映射：UX-DATA/Q-1 | P0 | open | ask_product

    {
      "question": "趋势统计的指标是什么，按什么时间维度归属和聚合？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "指标口径与时间维度均未定义。",
      "impact": "直接决定统计结果，缺失时无法验收。",
      "options": [
        "提供明确指标定义及时间归属规则",
        "先限定一个业务指标及时间维度",
        "其他或暂不确定"
      ],
      "recommendation": "建议提供指标、时间归属和聚合规则及示例，由产品确认，不自行指定口径。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-1"
    }

映射：UX-DATA/Q-2 | P0 | open | ask_product

    {
      "question": "状态和部门筛选的统计范围与明细范围如何对应？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "要求筛选及查看明细，但未定义联动和范围。",
      "impact": "影响统计数字与明细是否一致，可能造成错误解读。",
      "options": [
        "明细严格对应选中的统计范围与筛选",
        "明细采用不同范围并明确说明",
        "其他或暂不确定"
      ],
      "recommendation": "建议默认考虑统计与明细范围一致，具体规则待产品确认。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-2"
    }

映射：UX-DATA/Q-3 | P0 | open | ask_product

    {
      "question": "统计多久更新一次，用户应如何理解数据时间？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "刷新规则未定，结果时效影响统计解释。",
      "impact": "影响数据正确性预期与验收。",
      "options": [
        "按明确周期刷新并展示数据时间",
        "按查询时获取的数据计算",
        "其他或暂不确定"
      ],
      "recommendation": "建议先明确业务可接受的数据时效及展示要求，不预设刷新频率。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-3"
    }

映射：UX-DATA/Q-4 | P0 | open | ask_product

    {
      "question": "缺失、重复或异常数据在统计和明细中如何处理？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "异常数据处理未定。",
      "impact": "影响统计口径及明细对账。",
      "options": [
        "排除并明确提示",
        "纳入并标记异常",
        "按异常类型分别处理",
        "其他或暂不确定"
      ],
      "recommendation": "建议按异常类型明确处理及展示，待产品确认。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-4"
    }

映射：UX-DATA/Q-5 | P1 | open | ask_design

    {
      "question": "数据展示和明细查看的布局及空、异常状态如何设计？",
      "priority": "P1",
      "resolution": "ask_design",
      "reason": "未提供视觉稿及状态设计。",
      "impact": "影响筛选、阅读与明细定位体验。",
      "options": [
        "提供低保真布局与关键状态",
        "先提供交互说明",
        "其他或暂不确定"
      ],
      "recommendation": "建议口径明确后依据数据特点选择展示形式。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-5"
    }

映射：UX-DATA/Q-6 | P1 | open | ask_dev

    {
      "question": "现有数据源是否具备状态、部门、时间及明细字段，并支持所需刷新与筛选？",
      "priority": "P1",
      "resolution": "ask_dev",
      "reason": "没有数据字典或技术资料。",
      "impact": "影响数据可得性及技术方案；当前能力未知。",
      "options": [
        "核查数据字典、数据源及更新机制",
        "识别数据缺口并评估补充",
        "其他或暂不确定"
      ],
      "recommendation": "建议研发核对数据血缘和能力，不能从需求推断现有支持。",
      "status": "open",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-6"
    }

完成清单第 4 项未满足：
    实际模型登记的核心规则/设计待决事项未答，保留缺口

完成清单第 7 项未满足：
    实际模型登记的核心规则/设计待决事项未答，保留缺口

完成清单第 11 项未满足：
    实际模型登记的核心规则/设计待决事项未答，保留缺口

