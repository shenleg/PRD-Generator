# 简化交接草稿（非完整 PRD）

    内部服务按任务编号查询既有仿真结果

需求：PROBE-BACKEND；基于分析修订：1
analysis_status=completed；readiness=ready_for_document
待产品负责人确认；本工具不分配正式 PRD 编号、不发布。

## 分析条目摘录与映射

以下编号仅用于分析追溯，不是正式 PRD 需求编号。

### requirements.goals

映射：PROBE-BACKEND/GOAL-1 | tag=confirmed | status=active | 当前条目

    让内部服务按任务编号读取既有仿真结果。

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

映射：PROBE-BACKEND/SCN-1 | tag=confirmed | status=active | 当前条目

    内部服务使用既有服务身份，调用后端查询接口读取某任务的既有仿真结果，不涉及页面和用户交互。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至6行"
        }
      ]
    }

### requirements.functional_requirements

映射：PROBE-BACKEND/FR-1 | tag=confirmed | status=active | 当前条目

    新增后端查询接口，输入一个非空 task_id，成功返回该任务的 result_id 和 status。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至6行"
        }
      ],
      "related_ids": [
        "GOAL-1",
        "SCN-1"
      ]
    }

### requirements.business_rules

映射：PROBE-BACKEND/BR-1 | tag=confirmed | status=active | 当前条目

    任务不存在时返回 not_found。

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

映射：PROBE-BACKEND/BR-2 | tag=confirmed | status=active | 当前条目

    无权访问任务时返回 forbidden；调用方使用既有服务身份，本期不变更认证机制。

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

映射：PROBE-BACKEND/AC-1 | tag=confirmed | status=active | 当前条目

    提供存在且当前服务身份有权限的任务，以其非空 task_id 调用，返回内容包含该任务的 result_id 和 status。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第6至7行"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

映射：PROBE-BACKEND/AC-2 | tag=confirmed | status=active | 当前条目

    提供不存在的任务，以其非空 task_id 调用，返回 not_found。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第6至7行"
        }
      ],
      "related_ids": [
        "BR-1"
      ]
    }

映射：PROBE-BACKEND/AC-3 | tag=confirmed | status=active | 当前条目

    提供当前服务身份无权限的任务，以其非空 task_id 调用，返回 forbidden。

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

映射：PROBE-BACKEND/FR-2 | tag=confirmed | status=active | 当前条目

    本期新增供内部服务调用的按单个 task_id 读取既有仿真结果的后端查询接口。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至7行"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

### requirements.scope.out_of_scope

映射：PROBE-BACKEND/CON-1 | tag=confirmed | status=active | 当前条目

    不涉及页面和用户交互，不增加其他过滤条件，不分页，不改变结果计算，不变更认证机制。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第5至7行"
        }
      ]
    }

### business_assessment.flows

映射：PROBE-BACKEND/FLOW-1 | tag=confirmed | status=active | 当前条目

    内部服务以既有身份提交非空 task_id；存在且有权限则读取该任务 result_id、status；不存在返回 not_found；无权访问返回 forbidden。此为业务分支，不规定底层检查执行顺序。

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

映射：PROBE-BACKEND/BND-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    输入限定为一个非空 task_id，空值不符合声明的调用前提；不擅自增加过滤条件、批量或分页。非法格式的接口协议细节交研发结合既有契约确认，不新造业务错误码。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第6至7行"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-1"
      ]
    }

### business_assessment.exceptions

映射：PROBE-BACKEND/EXC-1 | tag=confirmed | status=active | 当前条目

    原文明示的业务异常为任务不存在和无权访问，分别使用 not_found、forbidden；查询既有结果不改变结果计算。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "第6至7行"
        }
      ],
      "related_ids": [
        "BR-1",
        "BR-2"
      ]
    }

## 遗留事项与问题记录

open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。

映射：PROBE-BACKEND/Q-1 | P1 | open | ask_dev

    {
      "question": "研发确认现有接口、既有服务身份权限判断和既有结果字段能否支持上述查询契约，并核对字段格式及非法输入沿用的接口协议。",
      "priority": "P1",
      "resolution": "ask_dev",
      "reason": "原文明示技术支持情况由研发确认，合成输入不能作为真实能力证据。",
      "impact": "影响接口实现和联调，不改变已明确的三类业务返回预期。",
      "options": [],
      "recommendation": "由研发对照现有接口及上述三组验收样本确认，不向产品索要实现承诺。",
      "status": "open",
      "related_ids": [
        "FR-1",
        "BR-2",
        "BND-1"
      ],
      "id": "Q-1"
    }

