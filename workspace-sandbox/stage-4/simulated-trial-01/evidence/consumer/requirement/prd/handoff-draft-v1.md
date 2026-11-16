# 简化交接草稿（非完整 PRD）

    办公采购申请批量撤回（模拟试用）

需求：SIM-PROCUREMENT-001；基于分析修订：5
analysis_status=completed；readiness=not_ready
待产品负责人确认；本工具不分配正式 PRD 编号、不发布。

> 风险：仅为初步草稿，存在未解决缺口，不能作为已就绪需求交付。

## 分析条目摘录与映射

以下编号仅用于分析追溯，不是正式 PRD 需求编号。

### requirements.goals

映射：SIM-PROCUREMENT-001/GOAL-1 | tag=confirmed | status=active | 当前条目

    减少申请填错或重复提交后，员工找采购同事退回的来回沟通；不编造节省时间或收益数字。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第1条"
        }
      ],
      "related_ids": []
    }

### requirements.scenarios

映射：SIM-PROCUREMENT-001/SCN-1 | tag=confirmed | status=active | 当前条目

    员工在现有采购申请网页列表中选择多条申请撤回，修正后重新提交；可操作角色与状态尚待澄清。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第1、3条"
        }
      ],
      "related_ids": [
        "GOAL-1"
      ]
    }

### requirements.functional_requirements

映射：SIM-PROCUREMENT-001/FR-1 | tag=confirmed | status=active | 当前条目

    在现有采购申请列表增加批量撤回能力；保留申请与审批历史，使申请能够修改后重新提交。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第1、5条"
        }
      ],
      "related_ids": [
        "GOAL-1",
        "SCN-1"
      ]
    }

### requirements.business_rules

映射：SIM-PROCUREMENT-001/BR-1 | tag=confirmed | status=to_reassess | 待重评，非确定内容

    原文候选口径：提交过的申请都应该能撤回；不是已裁决的最终状态范围。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第2条"
        }
      ],
      "related_ids": [
        "FR-1"
      ],
      "reason": "该原文候选口径已被第1轮模拟裁决否定或限定，保留原文来源，不再视为现行规则。"
    }

映射：SIM-PROCUREMENT-001/BR-2 | tag=confirmed | status=to_reassess | 待重评，非确定内容

    原文候选口径：只有待审批的申请可以撤回；与同条其他说法冲突。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第2条"
        }
      ],
      "related_ids": [
        "FR-1"
      ],
      "reason": "该原文候选口径已被第1轮模拟裁决否定或限定，保留原文来源，不再视为现行规则。"
    }

映射：SIM-PROCUREMENT-001/BR-3 | tag=confirmed | status=active | 当前条目

    原文候选口径：审批通过但还没下单的申请也应能撤回。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第2条"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-4 | tag=confirmed | status=active | 当前条目

    批量入口不能扩大既有数据可见范围；创建人与采购管理员的具体操作权限未定。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第3条"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-5 | tag=confirmed | status=active | 当前条目

    撤回不删除原申请，原审批记录必须保留。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第5条"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-6 | tag=confirmed | status=active | 当前条目

    一批中存在不能撤回的申请时，不应卡住其他申请；需要给出成功数、失败数及失败原因。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第4条"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-7 | tag=confirmed | status=active | 当前条目

    仅待审批，以及审批通过但尚未下单的申请允许撤回；已下单、执行采购、收货完成、已取消均不允许。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第1轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-1"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-8 | tag=confirmed | status=active | 当前条目

    本期只有申请创建人能撤回自己的申请；采购管理员不能代撤，不新增其他角色或代办权限，批量入口不扩大既有可见范围。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第1轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-2",
        "BR-4"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-9 | tag=confirmed | status=active | 当前条目

    按每条申请真正执行时的最新状态和权限判定。下单先成功则撤回失败并提示状态已变化、未撤回；撤回先成功则后续基于旧状态的下单或审批不得再成功；审批通过但未下单仍可撤回。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第1轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-3"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-10 | tag=confirmed | status=active | 当前条目

    撤回成功后原申请回到草稿，保留原申请编号与各次已存在的审批历史，允许修改后重新提交；旧待办及重提轮次尚待Q-8确认。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第1轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-4",
        "BR-5"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-11 | tag=confirmed | status=active | 当前条目

    逐条处理；不能撤的保持不变，不因一条失败回滚其他成功项。结果列成功数、失败数，每条失败给申请编号和原因；无权限不得泄漏申请详情。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第2轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-5",
        "BR-6"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-12 | tag=confirmed | status=active | 当前条目

    撤回成功后旧审批待办失效，审批人再操作明确提示申请已撤回且不再生效。原编号重提开启新审批轮次，不复用上次通过结果，各轮历史记录均保留。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第2轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-8",
        "BR-5",
        "BR-10"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-13 | tag=confirmed | status=active | 当前条目

    只处理本次勾选的可见行，不是筛选全量；翻页不保留勾选。沿用模拟业务方明确的单页最多20条，一批最多20条；空选不发请求，超过20条的请求整体拒绝且不改变任何申请。服务端仍须校验实际权限与状态。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第2轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-6",
        "BR-8"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-14 | tag=confirmed | status=active | 当前条目

    重复点击或网络重试时，已撤回申请不再执行撤回，返回已撤回，不重复写成功撤回日志。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第3轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-7"
      ]
    }

映射：SIM-PROCUREMENT-001/BR-15 | tag=confirmed | status=active | 当前条目

    沿用现有日志查询，不新增日志页面；至少可查操作人、时间、申请编号、原状态、新状态及逐条操作结果，失败原因也应可查询。现有能力是否具备仍由研发确认。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第3轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "CON-1",
        "Q-9",
        "Q-11"
      ]
    }

### requirements.constraints

映射：SIM-PROCUREMENT-001/CON-1 | tag=confirmed | status=active | 当前条目

    沿用现有网页列表与操作日志，不另建采购系统。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第6条"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

映射：SIM-PROCUREMENT-001/CON-2 | tag=confirmed | status=active | 当前条目

    本次不改变既有审批规则和采购下单规则。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第6条"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

### requirements.acceptance_criteria

映射：SIM-PROCUREMENT-001/AC-1 | tag=inferred | status=to_reassess | 待重评，非确定内容；推断，未经确认

    验收草案：从现有列表选择合法申请撤回，保留申请及审批历史并显示逐条结果；合法状态、权限、并发和重试结果仍待确认，不能作为完整验收。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第1、3、4、5条"
        }
      ],
      "related_ids": [
        "FR-1",
        "Q-1",
        "Q-2",
        "Q-3",
        "Q-7"
      ]
    }

映射：SIM-PROCUREMENT-001/AC-2 | tag=inferred | status=active | 当前条目；推断，未经确认

    创建人对自己待审批或通过未下单的申请成功撤回后，原申请回草稿、编号不变、原审批历史仍可查。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第1轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-7",
        "BR-8",
        "BR-10"
      ]
    }

映射：SIM-PROCUREMENT-001/AC-3 | tag=inferred | status=active | 当前条目；推断，未经确认

    非创建人、无权访问或执行时处于已下单/执行采购/收货完成/已取消状态的申请不能被撤回，不因批量入口扩大可见范围或改变该申请。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第1轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-7",
        "BR-8"
      ]
    }

映射：SIM-PROCUREMENT-001/AC-4 | tag=inferred | status=active | 当前条目；推断，未经确认

    分别让下单和撤回先成功：前者后续撤回失败并显示状态变化，后者后续旧状态下单/审批不再成功；审批先通过但未下单仍满足可撤范围。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第1轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-9"
      ]
    }

映射：SIM-PROCUREMENT-001/AC-5 | tag=inferred | status=active | 当前条目；推断，未经确认

    一批混有合法与不合法申请时，合法项成功撤回，失败项不变，不整批回滚；反馈成功数、失败数和各失败项原因，权限失败不泄露详情。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第2轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-11",
        "BR-7",
        "BR-8"
      ]
    }

映射：SIM-PROCUREMENT-001/AC-6 | tag=inferred | status=active | 当前条目；推断，未经确认

    撤回后用旧待办审批应提示已撤回且不生效；修改后以原编号重提应开启新一轮审批，不能直接沿用上次通过结果，旧轮记录仍可查。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第2轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-12",
        "BR-10"
      ]
    }

映射：SIM-PROCUREMENT-001/AC-7 | tag=inferred | status=active | 当前条目；推断，未经确认

    检查空选择不提交、翻页后不保留勾选；分别提交1、20和21条：合法边界批次逐条判断，21条整体拒绝且任一申请均未改变。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第2轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-13"
      ]
    }

映射：SIM-PROCUREMENT-001/AC-8 | tag=inferred | status=to_reassess | 待重评，非确定内容；推断，未经确认

    对已经成功撤回的申请重复提交时，应返回已撤回，不再次改变申请，不新增重复的成功撤回日志；该项汇总分类待Q-12，不把推荐选项当最终预期。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第3轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-14",
        "Q-12"
      ]
    }

映射：SIM-PROCUREMENT-001/AC-9 | tag=inferred | status=active | 当前条目；推断，未经确认

    成功与失败的逐条操作都能按申请编号查询到业务要求的操作人、时间、原新状态、结果及失败原因；不新增查询页面。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第3轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-15"
      ]
    }

### requirements.scope.in_scope

映射：SIM-PROCUREMENT-001/CON-3 | tag=confirmed | status=active | 当前条目

    现有网页列表上的批量撤回及其结果反馈、申请保留和重提衔接。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第1、4、5、6条"
        }
      ],
      "related_ids": [
        "FR-1"
      ]
    }

### requirements.scope.out_of_scope

映射：SIM-PROCUREMENT-001/CON-4 | tag=confirmed | status=active | 当前条目

    移动端与消息通知本期不做；不新建采购系统。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第6条"
        }
      ],
      "related_ids": []
    }

### business_assessment.flows

映射：SIM-PROCUREMENT-001/FLOW-1 | tag=inferred | status=active | 当前条目；推断，未经确认

    创建人从当前页勾选申请（空选不提交，超过20条整体拒绝）→逐条以执行时状态与权限判定→成功回原编号草稿、旧审批待办失效，失败项不变→展示逐条与汇总结果→修改后以原编号发起新审批轮次，保留各轮历史。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第1、2轮回答"
        }
      ],
      "related_ids": [
        "FR-1",
        "BR-7",
        "BR-8",
        "BR-9",
        "BR-10",
        "BR-11",
        "BR-12",
        "BR-13"
      ]
    }

### business_assessment.boundaries

映射：SIM-PROCUREMENT-001/BND-1 | tag=confirmed | status=active | 当前条目

    并发业务预期已明确：逐条按执行时最新状态和权限判断，下单与撤回只能按有效先后结果生效；具体实现机制仍待研发核查。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第1轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-9",
        "Q-11"
      ]
    }

映射：SIM-PROCUREMENT-001/BND-2 | tag=confirmed | status=active | 当前条目

    不同状态及执行时权限变化的混选批次按逐条执行结果处理，保留合法成功项，失败项不变且不给出无权访问的详情。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第2轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-11",
        "BR-7",
        "BR-8",
        "BR-9"
      ]
    }

映射：SIM-PROCUREMENT-001/BND-3 | tag=confirmed | status=active | 当前条目

    本次输入只含当前页明确勾选的可见申请，翻页清空勾选；0条不发送、1至20条进入逐条判断、超过20条整体拒绝且全不变。20来自第2轮模拟回答，不是分析者推定的系统事实。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第2轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-13"
      ]
    }

### business_assessment.exceptions

映射：SIM-PROCUREMENT-001/EXC-1 | tag=confirmed | status=active | 当前条目

    重复点击/网络重试遇到已撤回申请时，不再次执行，不重复成功撤回日志，返回已撤回；该项在成功/失败汇总中的分类尚待新问题确认。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第3轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "BR-14",
        "Q-12"
      ]
    }

### business_assessment.gaps

映射：SIM-PROCUREMENT-001/GAP-1 | tag=inferred | status=to_reassess | 待重评，非确定内容；推断，未经确认

    初始问题已由前三轮模拟回答处理；当前业务阻塞转由独立的新汇总分类缺口记录，研发能力仍待Q-10/Q-11核查。本条保留初始缺口的追溯，不作为未回答的原问题重复追问。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第3轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "Q-12",
        "Q-10",
        "Q-11"
      ]
    }

映射：SIM-PROCUREMENT-001/GAP-2 | tag=inferred | status=active | 当前条目；推断，未经确认

    重复项不再次执行，但在成功/失败汇总中的归类未定；不能自行决定计成功、计失败或新增汇总分类。

    {
      "sources": [
        {
          "type": "user_answer",
          "location": "模拟业务方第3轮回答；助手构造，非真实用户产品决定"
        }
      ],
      "related_ids": [
        "Q-12",
        "BR-11",
        "BR-14"
      ]
    }

### business_assessment.conflicts

映射：SIM-PROCUREMENT-001/CNF-1 | tag=inferred | status=to_reassess | 待重评，非确定内容；推断，未经确认

    第2条同时出现全部已提交、仅待审批、通过但未下单也可撤回，当前无法视作同一状态规则。

    {
      "sources": [
        {
          "type": "input_document",
          "source_id": "SRC-1",
          "location": "模拟原文第2条"
        }
      ],
      "related_ids": [
        "BR-1",
        "BR-2",
        "BR-3"
      ],
      "related_question": "Q-1",
      "reason": "Q-1已裁决；保留初始冲突证据，当前口径由新规则单独表达。"
    }

## 遗留事项与问题记录

open/provisional/risk_accepted 及 ask_dev 项保持原状态；推荐选项不是已确认答案。

映射：SIM-PROCUREMENT-001/Q-1 | P0 | answered | ask_product

    {
      "question": "最终允许撤回哪些状态的申请？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "模拟业务方第1轮明确回答；保留原始问题与实际模拟答案。",
      "impact": "无法判定合法撤回状态。",
      "options": [
        "仅待审批",
        "待审批和审批通过但未下单",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议待审批及通过未下单均可，能满足更正诉求，但必须由业务确认。",
      "status": "answered",
      "related_ids": [
        "BR-1",
        "BR-2",
        "BR-3"
      ],
      "id": "Q-1",
      "answer": "以这次明确的口径为准：待审批，以及审批通过但还没下单，这两类允许撤回。已经下单、执行采购、收货完成或已取消的都不允许。成功后原申请回到草稿，保留原申请编号和历史审批记录，可以修改后重新提交。"
    }

映射：SIM-PROCUREMENT-001/Q-2 | P0 | answered | ask_product

    {
      "question": "本期谁能撤回哪些人的申请？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "模拟业务方第1轮明确回答；保留原始问题与实际模拟答案。",
      "impact": "可能引入越权批量操作。",
      "options": [
        "仅创建人撤自己的",
        "创建人加采购管理员代撤",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议仅创建人，先保持最小权限边界。",
      "status": "answered",
      "related_ids": [
        "BR-4"
      ],
      "id": "Q-2",
      "answer": "本期只有申请创建人能撤回自己的申请。采购管理员也不能代撤，其他角色和代办权限这期不做；批量入口不扩大现有可见范围。"
    }

映射：SIM-PROCUREMENT-001/Q-3 | P0 | answered | ask_product

    {
      "question": "撤回与审批或下单同时发生时，以什么业务结果判定成功或失败？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "模拟业务方第1轮明确回答；保留原始问题与实际模拟答案。",
      "impact": "可能出现撤回与下单均成功的矛盾。",
      "options": [
        "执行时最新状态与权限逐条判定，先成功者生效",
        "以页面打开时状态为准",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议以执行时最新状态判定，并明确先后动作的业务结果；实现方式交研发。",
      "status": "answered",
      "related_ids": [
        "BND-1",
        "FR-1"
      ],
      "id": "Q-3",
      "answer": "按每条申请真正执行时的最新状态和权限判定，不以打开页面时的快照为准。审批通过但未下单仍允许撤回；下单先成功则撤回失败并提示状态已变化，未撤回；撤回先成功则后续旧状态下单或审批不得再成功。具体怎么实现交研发确认。"
    }

映射：SIM-PROCUREMENT-001/Q-4 | P0 | answered | ask_product

    {
      "question": "撤回成功后原申请变为什么状态，重新提交是否沿用申请编号？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "模拟业务方第1轮已明确；Q-4为状态回答中主动补充的撤回去向及编号，不重复追问。",
      "impact": "核心状态流程不能还原。",
      "options": [
        "原申请回草稿并沿用编号",
        "产生新的申请",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议回草稿保留原申请编号，避免历史断链。",
      "status": "answered",
      "related_ids": [
        "FLOW-1",
        "BR-5"
      ],
      "id": "Q-4",
      "answer": "以这次明确的口径为准：待审批，以及审批通过但还没下单，这两类允许撤回。已经下单、执行采购、收货完成或已取消的都不允许。成功后原申请回到草稿，保留原申请编号和历史审批记录，可以修改后重新提交。"
    }

映射：SIM-PROCUREMENT-001/Q-5 | P0 | answered | ask_product

    {
      "question": "同批部分失败时，已成功项是否保留，结果逐条需要显示什么？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "模拟业务方第2轮已明确回答，保留原问题与本轮实际输入。",
      "impact": "无法验收混选批次。",
      "options": [
        "逐条处理，保留成功并给失败原因",
        "任一失败则整批不变",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议逐条处理，与原文部分失败不阻塞意图一致。",
      "status": "answered",
      "related_ids": [
        "BR-6",
        "BND-2"
      ],
      "id": "Q-5",
      "answer": "逐条处理，能撤的成功，不能撤的保持不变，不因为其中一条失败回滚其他成功项。结果要列成功数、失败数和每条失败的申请编号、原因；无权限不能泄露申请详情。"
    }

映射：SIM-PROCUREMENT-001/Q-6 | P0 | answered | ask_product

    {
      "question": "一次提交对应哪些已选申请，空选择、最大数量及超限时如何处理？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "模拟业务方第2轮已明确回答，保留原问题与本轮实际输入。",
      "impact": "输入范围和边界验收不明确。",
      "options": [
        "只处理当前明确勾选的申请，明确单批边界",
        "处理筛选结果全量",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议仅明确勾选范围；上限须业务结合实际列表确认，不能凭空给数。",
      "status": "answered",
      "related_ids": [
        "BND-3"
      ],
      "id": "Q-6",
      "answer": "仅处理本次勾选的可见行，不是筛选结果全量；翻页不保留勾选，沿用列表单页最多20条，所以一批最多20条。提交时空选不发送请求；超过20条的请求整体拒绝且不改变任何申请。不能因页面上不展示就省略服务端的权限和状态判断。"
    }

映射：SIM-PROCUREMENT-001/Q-7 | P0 | answered | ask_product

    {
      "question": "重复点击或重试遇到已撤回申请时，业务结果和成功日志如何处理？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "模拟业务方第3轮已回答重复撤回行为及最小审计信息；没有提供已撤回项的批次汇总分类。",
      "impact": "同一撤回的业务含义及重试验收不明确。",
      "options": [
        "返回已撤回，不再次撤回或重复成功留痕",
        "按新撤回再次处理",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议已撤回不再执行，用可识别结果防重复。",
      "status": "answered",
      "related_ids": [
        "EXC-1"
      ],
      "id": "Q-7",
      "answer": "重复点击或网络重试时已经撤回的申请不再执行一次撤回，返回已撤回，不重复写成功撤回日志。操作日志至少能查操作人、时间、申请编号、原状态、新状态和逐条操作结果；失败原因也要能查，不要求这次新增日志页面。"
    }

映射：SIM-PROCUREMENT-001/Q-8 | P0 | answered | ask_product

    {
      "question": "撤回后旧审批待办如何失效，重提是否启动新审批轮次？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "模拟业务方第2轮已明确回答，保留原问题与本轮实际输入。",
      "impact": "旧审批可能继续生效或错误沿用上次结果。",
      "options": [
        "旧待办失效，重提开启新审批轮次",
        "沿用原审批待办与通过结果",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议保留历史但开启新轮次，避免旧决定套用修改后的申请。",
      "status": "answered",
      "related_ids": [
        "BR-5",
        "FLOW-1"
      ],
      "id": "Q-8",
      "answer": "撤回成功后旧审批待办失效，审批人再操作要明确提示申请已撤回，不能继续生效。重提仍用原申请编号，但是新开一轮审批，不复用上次通过结果；历史各轮审批记录都保留。"
    }

映射：SIM-PROCUREMENT-001/Q-9 | P1 | answered | ask_product

    {
      "question": "沿用日志时至少需要哪些可查询信息，本期是否需要新增查询页面？",
      "priority": "P1",
      "resolution": "ask_product",
      "reason": "模拟业务方第3轮已回答重复撤回行为及最小审计信息；没有提供已撤回项的批次汇总分类。",
      "impact": "影响操作追溯及范围。",
      "options": [
        "记录逐条操作与结果，沿用查询页面",
        "只记录批次数量汇总",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议保留逐条结果以便追溯失败。",
      "status": "answered",
      "related_ids": [
        "CON-1"
      ],
      "id": "Q-9",
      "answer": "重复点击或网络重试时已经撤回的申请不再执行一次撤回，返回已撤回，不重复写成功撤回日志。操作日志至少能查操作人、时间、申请编号、原状态、新状态和逐条操作结果；失败原因也要能查，不要求这次新增日志页面。"
    }

映射：SIM-PROCUREMENT-001/Q-10 | P1 | open | ask_dev

    {
      "question": "是否有可复用的批量接口，现有权限与状态校验能否覆盖本次操作？",
      "priority": "P1",
      "resolution": "ask_dev",
      "reason": "原文第7条要求核查，未提供接口资料。",
      "impact": "研发需确认复用范围，不能假设已有能力。",
      "options": [
        "已有且满足",
        "需要新增或调整",
        "其他",
        "暂不确定"
      ],
      "recommendation": "由研发查接口及权限资料确认，不由产品保证实现。",
      "status": "open",
      "related_ids": [
        "FR-1",
        "CON-1"
      ],
      "id": "Q-10"
    }

映射：SIM-PROCUREMENT-001/Q-11 | P1 | open | ask_dev

    {
      "question": "现有状态变更、并发控制和日志字段能否支撑确认后的业务预期？",
      "priority": "P1",
      "resolution": "ask_dev",
      "reason": "尚无系统或技术资料。",
      "impact": "影响实现与测试准备。",
      "options": [
        "现有能力满足",
        "需要补充改造",
        "其他",
        "暂不确定"
      ],
      "recommendation": "研发核实能力与影响，不预设数据库锁或事务方案。",
      "status": "open",
      "related_ids": [
        "BND-1",
        "EXC-1",
        "CON-1"
      ],
      "id": "Q-11"
    }

映射：SIM-PROCUREMENT-001/Q-12 | P0 | open | ask_product

    {
      "question": "已撤回的重复项，应计入成功数、失败数，还是另列“未执行/已撤回”数量？",
      "priority": "P0",
      "resolution": "ask_product",
      "reason": "Q-7已明确重复项不再次执行，Q-5此前要求成功/失败汇总；两条合在一起仍缺少重复项的汇总分类。这是新输出决策，不重复询问已明确的重试行为。",
      "impact": "同一批次含重复已撤回项时，无法判定成功/失败汇总的正确数字。",
      "options": [
        "计入失败，原因已撤回",
        "计入成功，但说明未再次执行",
        "单列未执行/已撤回",
        "其他",
        "暂不确定"
      ],
      "recommendation": "建议单列未执行/已撤回，避免将未发生的撤回计为本次成功；需业务明确采用，当前仅是推荐。",
      "status": "open",
      "related_ids": [
        "BR-11",
        "BR-14"
      ],
      "id": "Q-12"
    }

完成清单第 4 项未满足：
    含重复已撤回项的批次汇总分类未定，核心输出验收仍缺可判定口径。

完成清单第 6 项未满足：
    含重复已撤回项的批次汇总分类未定，核心输出验收仍缺可判定口径。

完成清单第 7 项未满足：
    含重复已撤回项的批次汇总分类未定，核心输出验收仍缺可判定口径。

