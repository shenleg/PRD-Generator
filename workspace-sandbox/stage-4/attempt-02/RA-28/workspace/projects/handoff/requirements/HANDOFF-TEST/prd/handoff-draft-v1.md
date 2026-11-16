# 简化交接草稿（非完整 PRD）

    合成测试，不是真实需求

需求：HANDOFF-TEST；基于分析修订：1
analysis_status=completed；readiness=conditionally_ready
待产品负责人确认；本工具不分配正式 PRD 编号、不发布。

> 条件就绪：遗留事项、暂定假设与研发确认项仍需处理。

## 分析条目摘录与映射

以下编号仅用于分析追溯，不是正式 PRD 需求编号。

### requirements.goals

映射：HANDOFF-TEST/GOAL-1 | tag=confirmed | status=active | 当前条目

    已确认目标

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "合成测试输入"
        }
      ]
    }

### requirements.functional_requirements

映射：HANDOFF-TEST/FR-1 | tag=confirmed | status=active | 当前条目

    合成查询功能

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "合成测试输入"
        }
      ]
    }

### requirements.acceptance_criteria

映射：HANDOFF-TEST/AC-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    合成验收条件

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "合成测试输入"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

### business_assessment.boundaries

映射：HANDOFF-TEST/BND-1 | tag=inferred | status=to_reassess | 待重评，非确定内容；推断，未经确认

    合成待重评边界

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "合成测试输入"
        }
      ]
    }

### assumptions

映射：HANDOFF-TEST/ASM-1 | tag=assumption | status=active | 当前条目；暂定假设，待验证

    合成暂定范围

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "合成测试输入"
        }
      ],
      "related_question": "Q-1",
      "basis": "合成推荐依据",
      "verification": "产品负责人后续核对合成输入"
    }

## 遗留事项与问题记录

open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。

映射：HANDOFF-TEST/Q-1 | P1 | provisional | ask_product

    {
      "question": "合成范围如何验证？",
      "priority": "P1",
      "resolution": "ask_product",
      "reason": "暂定",
      "impact": "范围",
      "options": [
        "甲",
        "乙"
      ],
      "recommendation": "暂用甲",
      "status": "provisional",
      "related_ids": [
        "FR-1"
      ],
      "id": "Q-1"
    }

