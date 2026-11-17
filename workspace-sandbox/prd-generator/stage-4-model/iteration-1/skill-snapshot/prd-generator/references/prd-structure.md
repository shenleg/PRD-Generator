# PRD 结构与模板适配

默认顺序及来源如下。必有章节为空写“分析结果中无此项”；可选分析缺省时省略章节并列入文档信息的未覆盖分析项。用户模板可调整标题和布局，但映射、身份、追溯、标注不变，文首仍依次为草稿提示、文档信息、变更记录。

| 键 | 章节 | 来源 | 必有 |
| --- | --- | --- | --- |
| info | 文档信息 | `requirement.json`、`meta`、`context` | 是 |
| changes | 变更记录 | `prd-events.jsonl` | 是 |
| background | 背景与价值 | `value_assessment` | 否 |
| scope | 目标与范围 | `requirements.goals`、`scope` | 是 |
| scenarios | 用户与场景 | `requirements.scenarios` | 是 |
| functional_requirements | 功能需求 | `requirements.functional_requirements` | 是 |
| business_rules | 业务规则 | `requirements.business_rules` | 是 |
| flows_states | 流程与状态 | `business_assessment.flows`、`states` | 否 |
| boundaries_exceptions | 边界与异常 | `business_assessment.boundaries`、`exceptions` | 是 |
| constraints | 约束与非功能需求 | `requirements.constraints`、`non_functional_requirements` | 否 |
| acceptance_criteria | 验收条件 | `requirements.acceptance_criteria` | 是 |
| ux | 界面与交互 | `ux_assessment` | 否 |
| technical | 技术说明与研发确认项 | `technical_feasibility`、`questions` 中 `ask_dev` | 否 |
| impact | 关联与影响 | `impact_analysis` | 否 |
| residuals | 遗留事项 | `questions`、`assumptions`、`gaps`、`conflicts`、`decisions` | 是 |
| appendix | 附录 | `context.domain_terms`、来源 `source_id` | 是 |

文档信息由脚本渲染，包含需求编号、标题、PRD 版本、状态、草稿类型、基于的分析修订号、生成时间和未覆盖分析项。功能需求及验收条件用带“分析来源”列的表格。分析未给出的功能关联不自行补上。

各章节用 `<!-- prd:section <key> -->` 和 `<!-- /prd:section -->`；正式条目用 `<!-- prd:item <prd_id> -->` 与 `<!-- /prd:item -->`，缺口占位用 `<!-- prd:gap <gap_id> -->` 与 `<!-- /prd:gap -->`，遗留项用 `<!-- prd:residual <reference> -->` 与 `<!-- /prd:residual -->`。章节可包含其他块，其他块不得嵌套；禁止重复、交叉和不成对。表格标记放单元格内。标记只是机器定位，不能代替语义核查。
