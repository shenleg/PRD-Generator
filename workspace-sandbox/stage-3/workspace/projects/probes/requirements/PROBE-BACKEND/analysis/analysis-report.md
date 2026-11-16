# PROBE-BACKEND：需求分析报告

本报告由主会话按用户明确调整的分工独立整理。唯一权威为同目录 analysis-result.json；本报告是数据视图，不新增业务结论。

## 1. 理解摘要

| 编号 | 内容 | 标签 | 状态 | 关联 | 来源 |
| --- | --- | --- | --- | --- | --- |
| GOAL-1 | 让内部服务按任务编号读取既有仿真结果。 | confirmed | active |  | SRC-1：第5行 |
| SCN-1 | 内部服务使用既有服务身份，调用后端查询接口读取某任务的既有仿真结果，不涉及页面和用户交互。 | confirmed | active |  | SRC-1：第5至6行 |

### 本期包含

| 编号 | 内容 | 标签 | 状态 | 关联 | 来源 |
| --- | --- | --- | --- | --- | --- |
| FR-2 | 本期新增供内部服务调用的按单个 task_id 读取既有仿真结果的后端查询接口。 | confirmed | active | FR-1 | SRC-1：第5至7行 |

### 本期不含

| 编号 | 内容 | 标签 | 状态 | 关联 | 来源 |
| --- | --- | --- | --- | --- | --- |
| CON-1 | 不涉及页面和用户交互，不增加其他过滤条件，不分页，不改变结果计算，不变更认证机制。 | confirmed | active |  | SRC-1：第5至7行 |

## 2. 已确认事项

仅下表中 active 的记录表示当前确认内容；其余状态不可视为当前确定结论。

| 编号 | 内容 | 标签 | 状态 | 关联 | 来源 |
| --- | --- | --- | --- | --- | --- |
| GOAL-1 | 让内部服务按任务编号读取既有仿真结果。 | confirmed | active |  | SRC-1：第5行 |
| SCN-1 | 内部服务使用既有服务身份，调用后端查询接口读取某任务的既有仿真结果，不涉及页面和用户交互。 | confirmed | active |  | SRC-1：第5至6行 |
| FR-1 | 新增后端查询接口，输入一个非空 task_id，成功返回该任务的 result_id 和 status。 | confirmed | active | GOAL-1、SCN-1 | SRC-1：第5至6行 |
| BR-1 | 任务不存在时返回 not_found。 | confirmed | active | FR-1 | SRC-1：第6行 |
| BR-2 | 无权访问任务时返回 forbidden；调用方使用既有服务身份，本期不变更认证机制。 | confirmed | active | FR-1 | SRC-1：第6行 |
| AC-1 | 提供存在且当前服务身份有权限的任务，以其非空 task_id 调用，返回内容包含该任务的 result_id 和 status。 | confirmed | active | FR-1 | SRC-1：第6至7行 |
| AC-2 | 提供不存在的任务，以其非空 task_id 调用，返回 not_found。 | confirmed | active | BR-1 | SRC-1：第6至7行 |
| AC-3 | 提供当前服务身份无权限的任务，以其非空 task_id 调用，返回 forbidden。 | confirmed | active | BR-2 | SRC-1：第6至7行 |
| FLOW-1 | 内部服务以既有身份提交非空 task_id；存在且有权限则读取该任务 result_id、status；不存在返回 not_found；无权访问返回 forbidden。此为业务分支，不规定底层检查执行顺序。 | confirmed | active | FR-1、BR-1、BR-2 | SRC-1：第5至7行 |
| EXC-1 | 原文明示的业务异常为任务不存在和无权访问，分别使用 not_found、forbidden；查询既有结果不改变结果计算。 | confirmed | active | BR-1、BR-2 | SRC-1：第6至7行 |
| FR-2 | 本期新增供内部服务调用的按单个 task_id 读取既有仿真结果的后端查询接口。 | confirmed | active | FR-1 | SRC-1：第5至7行 |
| CON-1 | 不涉及页面和用户交互，不增加其他过滤条件，不分页，不改变结果计算，不变更认证机制。 | confirmed | active |  | SRC-1：第5至7行 |

## 3. 业务价值分析

```json
{
  "problem": "调用方需要按任务编号读取既有仿真结果。",
  "affected_users": [
    "内部服务调用方"
  ],
  "expected_benefits": [
    "可按任务编号读取既有仿真结果"
  ],
  "business_value": "unknown",
  "necessity": "necessary"
}
```

## 4. 缺口与矛盾

当前数组为空；不据此推导已完成分析或不存在风险。

## 5. 待回答问题

下列是登记清单，不表示本轮继续提问；实际提问以 turn-NN.json 为准。

此分类当前没有问题记录。

## 6. 暂定假设

推荐语不等于已采用假设，只有 active 假设支撑当前结论。

当前数组为空；不据此推导已完成分析或不存在风险。

## 7. 研发确认项

登记当前能力核查，不要求产品作技术实现承诺。

- **Q-1 / P1 / ask_dev / open**：研发确认现有接口、既有服务身份权限判断和既有结果字段能否支持上述查询契约，并核对字段格式及非法输入沿用的接口协议。
  - 原因：原文明示技术支持情况由研发确认，合成输入不能作为真实能力证据。；影响：影响接口实现和联调，不改变已明确的三类业务返回预期。
  - 关联：FR-1、BR-2、BND-1
  - 选项：无交互选项
  - 推荐：由研发对照现有接口及上述三组验收样本确认，不向产品索要实现承诺。

## 8. 边界与异常

inferred 的候选场景不是已确认的处理规则。

| 编号 | 内容 | 标签 | 状态 | 关联 | 来源 |
| --- | --- | --- | --- | --- | --- |
| BND-1 | 输入限定为一个非空 task_id，空值不符合声明的调用前提；不擅自增加过滤条件、批量或分页。非法格式的接口协议细节交研发结合既有契约确认，不新造业务错误码。 | inferred | active | FR-1、Q-1 | SRC-1：第6至7行 |
| EXC-1 | 原文明示的业务异常为任务不存在和无权访问，分别使用 not_found、forbidden；查询既有结果不改变结果计算。 | confirmed | active | BR-1、BR-2 | SRC-1：第6至7行 |

## 9. 验收条件

待重评草案不能作为已完成的可执行验收。

| 编号 | 内容 | 标签 | 状态 | 关联 | 来源 |
| --- | --- | --- | --- | --- | --- |
| AC-1 | 提供存在且当前服务身份有权限的任务，以其非空 task_id 调用，返回内容包含该任务的 result_id 和 status。 | confirmed | active | FR-1 | SRC-1：第6至7行 |
| AC-2 | 提供不存在的任务，以其非空 task_id 调用，返回 not_found。 | confirmed | active | BR-1 | SRC-1：第6至7行 |
| AC-3 | 提供当前服务身份无权限的任务，以其非空 task_id 调用，返回 forbidden。 | confirmed | active | BR-2 | SRC-1：第6至7行 |

## 10. 历史需求关联

本阶段未开展历史检索或基线对照，不能宣称与历史无冲突。

## 11. 技术可行性及风险

本阶段不开展技术可行性评估，现有能力由研发确认；缺省或 unknown 均不表示已有依据支持。

## 12. 用户体验和设计建议

仅保留当前界面依赖判断及登记事项，不扩展完整视觉设计。

```json
{
  "ui_dependent": false
}
```

## 13. 结论与就绪度

- 分析修订号：`1`；来源修订号：`1`。
- 分析状态：`completed`。
- 就绪度：`ready_for_document`。
- 实际校验：`pass`。数据合法不代表业务已就绪。
- **仍 open 的 P0：无。**

可进入正式 PRD 草稿流程，但不代表研发已全部确认或产品批准发布。

### 决策记录

当前数组为空；不据此推导已完成分析或不存在风险。

### 完成清单记录

```json
[
  {
    "item": 1,
    "satisfied": true,
    "question_refs": [],
    "reason": "目标和原因均明确：供调用方按任务编号读取既有仿真结果。"
  },
  {
    "item": 2,
    "satisfied": true,
    "question_refs": [],
    "reason": "核心调用方为内部服务，以既有服务身份查询单任务结果，无页面交互。"
  },
  {
    "item": 3,
    "satisfied": true,
    "question_refs": [],
    "reason": "非空 task_id 调用以及成功、不存在、无权限分支可还原，无需追加页面流程。"
  },
  {
    "item": 4,
    "satisfied": true,
    "question_refs": [],
    "reason": "成功字段、两类业务失败返回、身份与认证边界均已明确，不自行设计实现细节。"
  },
  {
    "item": 5,
    "satisfied": true,
    "question_refs": [],
    "reason": "本份输入内部无相互冲突的业务陈述。"
  },
  {
    "item": 6,
    "satisfied": true,
    "question_refs": [
      "Q-1"
    ],
    "reason": "当前声明的非空单编号调用边界、不存在和无权访问均已分析；空输入不属于合约前提，协议细节交研发核对，不扩展为新的核心业务场景。"
  },
  {
    "item": 7,
    "satisfied": true,
    "question_refs": [],
    "reason": "原文给出三组可构造样本及可判定的返回预期，逐项形成验收条件。"
  },
  {
    "item": 8,
    "satisfied": true,
    "question_refs": [],
    "reason": "本阶段未开展历史检索或基线对照，已明确声明。"
  },
  {
    "item": 9,
    "satisfied": true,
    "question_refs": [
      "Q-1"
    ],
    "reason": "技术能力未评估；按原文登记研发确认，不把合成输入当作现有支持证据。"
  },
  {
    "item": 10,
    "satisfied": true,
    "question_refs": [],
    "reason": "原文明确不涉及页面和用户交互，ui_dependent=false。"
  },
  {
    "item": 11,
    "satisfied": true,
    "question_refs": [
      "Q-1"
    ],
    "reason": "仅保留研发能力和协议核对事项，无未确认的产品核心规则或已采用假设；可形成需求草稿，不等于研发已确认。"
  }
]
```

### 未开展的分析

历史检索与基线对照、技术可行性结论和完整视觉分析不在本阶段范围；报告没有把这些缺省解释为已评估无问题。
