# 简化交接草稿（非完整 PRD）

    任务成功完成后邮件通知创建者

需求：PROBE-NOTIFICATION；基于分析修订：1
analysis_status=clarifying；readiness=conditionally_ready
待产品负责人确认；本工具不分配正式 PRD 编号、不发布。

> 条件就绪：遗留事项、暂定假设与研发确认项仍需处理。

## 分析条目摘录与映射

以下编号仅用于分析追溯，不是正式 PRD 需求编号。

### requirements.goals

映射：PROBE-NOTIFICATION/GOAL-1 | tag=confirmed | status=active | 当前条目

    新增任务成功完成邮件通知。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5行"
        }
      ]
    }

### requirements.scenarios

映射：PROBE-NOTIFICATION/SCN-1 | tag=confirmed | status=active | 当前条目

    任务 succeeded 时，通过任务创建者已登记的邮箱向其发送完成通知。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5行"
        }
      ]
    }

### requirements.functional_requirements

映射：PROBE-NOTIFICATION/FR-1 | tag=confirmed | status=active | 当前条目

    成功完成任务向创建者发送邮件，内容仅含 task_id、完成状态和既有结果链接。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5行"
        }
      ],
      "related_ids": [
        "GOAL-1",
        "SCN-1"
      ]
    }

### requirements.business_rules

映射：PROBE-NOTIFICATION/BR-1 | tag=confirmed | status=active | 当前条目

    仅 succeeded 时触发，失败和取消不通知；同一任务的完成通知不重复发送。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至6行"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

映射：PROBE-NOTIFICATION/BR-2 | tag=confirmed | status=active | 当前条目

    邮箱缺失或发送失败时记录失败原因，不改变任务状态；本期不增加重试功能。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第6行"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

### requirements.acceptance_criteria

映射：PROBE-NOTIFICATION/AC-1 | tag=confirmed | status=active | 当前条目

    创建者邮箱有效的成功任务应产生一封邮件，仅包含 task_id、完成状态和既有结果链接，接收人为创建者登记邮箱。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5、第7行"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

映射：PROBE-NOTIFICATION/AC-2 | tag=confirmed | status=active | 当前条目

    失败任务、取消任务和重复完成事件均不新增邮件。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第7行"
        }
      ],
      "related_ids": [
        "BR-1"
      ]
    }

映射：PROBE-NOTIFICATION/AC-3 | tag=confirmed | status=active | 当前条目

    缺少邮箱或发送失败时，有记录失败原因的失败记录，且任务状态保持不变。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第6至7行"
        }
      ],
      "related_ids": [
        "BR-2"
      ]
    }

### requirements.scope.in_scope

映射：PROBE-NOTIFICATION/FR-2 | tag=confirmed | status=active | 当前条目

    本期包含成功任务的创建者邮件通知、同任务不重复发送，以及邮箱缺失和发送失败的原因记录。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至7行"
        }
      ],
      "related_ids": [
        "FR-1",
        "BR-1",
        "BR-2"
      ]
    }

### requirements.scope.out_of_scope

映射：PROBE-NOTIFICATION/CON-1 | tag=confirmed | status=active | 当前条目

    本期不增加订阅、界面或重试功能；失败和取消任务不通知；不增加 task_id、完成状态和既有结果链接之外的邮件内容。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至6行"
        }
      ]
    }

### business_assessment.flows

映射：PROBE-NOTIFICATION/FLOW-1 | tag=confirmed | status=active | 当前条目

    任务成功完成后，按同任务不重复发送的规则向创建者登记邮箱发出指定内容邮件；失败、取消和重复完成事件不新增邮件；无邮箱或发送失败则留失败原因且不改变任务状态。这里只描述业务结果，不规定去重与发送的技术执行顺序。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至7行"
        }
      ],
      "related_ids": [
        "FR-1",
        "BR-1",
        "BR-2"
      ]
    }

### business_assessment.boundaries

映射：PROBE-NOTIFICATION/BND-1 | tag=confirmed | status=active | 当前条目

    重复完成事件不新增邮件；失败和取消任务不发送。去重规则的业务目标已明确，实现由研发确认，不向产品重复提问去重机制。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至7行"
        }
      ],
      "related_ids": [
        "BR-1",
        "Q-2"
      ]
    }

### business_assessment.exceptions

映射：PROBE-NOTIFICATION/EXC-1 | tag=confirmed | status=active | 当前条目

    缺少创建者邮箱或邮件发送失败均留下失败记录，任务状态不变；不增加重试功能。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第6至7行"
        }
      ],
      "related_ids": [
        "BR-2"
      ]
    }

### business_assessment.gaps

映射：PROBE-NOTIFICATION/GAP-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    新增邮件通知的业务原因未说明；不能擅自认定是减少轮询、避免遗漏或合规要求。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至7行，给出功能与规则，未说明原因"
        }
      ],
      "related_ids": [
        "Q-1"
      ]
    }

## 遗留事项与问题记录

open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。

映射：PROBE-NOTIFICATION/Q-1 | P1 | open | ask_product

    {
      "question": "新增成功完成邮件通知，主要是为了解决什么问题？",
      "priority": "P1",
      "resolution": "ask_product",
      "reason": "新增功能未给出原因，补充一句定性原因即可，不要求频率、成本或 ROI。",
      "impact": "不影响当前通知规则和验收表达，但业务背景仍缺一项。",
      "options": [
        "A. 让创建者及时得知完成，减少主动查询",
        "B. 避免创建者遗漏完成结果",
        "C. 其他，请简述实际原因",
        "D. 暂不确定"
      ],
      "recommendation": "建议从最贴近实际的 A 或 B 选一个作为主要原因；若均不符选 C。具体原因必须由你确认，目前不采用任何选项。",
      "status": "open",
      "related_ids": [
        "GOAL-1",
        "GAP-1"
      ],
      "id": "Q-1"
    }

映射：PROBE-NOTIFICATION/Q-2 | P1 | open | ask_dev

    {
      "question": "研发确认现有邮件发送能力、已登记邮箱和既有结果链接的获取，以及满足同任务不重复发送与失败留痕的实现支持。",
      "priority": "P1",
      "resolution": "ask_dev",
      "reason": "原文明示发送能力及去重实现由研发确认，未提供真实技术证据。",
      "impact": "影响实现与联调，不改变已明确的通知业务规则。",
      "options": [],
      "recommendation": "研发对照成功、失败、取消、重复事件、邮箱缺失和发送失败样例确认支持与限制。",
      "status": "open",
      "related_ids": [
        "FR-1",
        "BR-1",
        "BR-2"
      ],
      "id": "Q-2"
    }

