# 补丁与增量更新

本文件负责五种工作方式、补丁协议及写入边界；首次保存和后续每次更新均读取。模型负责语义判断及影响清单，`scripts/update_analysis.py` 负责编号、校验、并发保护和持久化。

## 五种工作方式

| change_type | 处理规则 |
| --- | --- |
| initial_analysis | 首次分析；base_revision=0；抽取原文、登记缺口，脚本创建工作区记录及需求目录。 |
| supplement | 补充及答疑；只更新受影响条目，发现新规则、边界或矛盾；已回答的问题不重复问。 |
| correction | 用户明示更正；保留旧内容和证据，重评相关规则、假设、验收；推断不能覆盖 confirmed。 |
| withdrawal | 用户明确撤销；withdraw 保留原条目，关联问题 dropped、关联验收及其他依赖待重评。 |
| new_source_version | 逐项对照旧、新原文，列新增/删除/修改/未变；先保存 stale 的受影响集，再在后续补丁中完成重评。 |

每轮：读取当前 JSON、来源和 revision → 确定变化及直接/间接影响 → 标记或完成重评 → 检查问题及十一项完成清单 → 生成补丁 → 脚本预检并保存 → 从保存结果整理报告。用户结束只停止追问，不关闭缺口。

新版文档新增一个来源版本，不覆盖旧来源；新旧路径由用户提供，脚本不写 inputs/。已关闭问题在相关依据变化时用 update 重开，保留旧 answer 并在 reason 解释重开原因。未变化条目不更新。重评尚未完成时保持 stale/not_ready，warning 可以保存但须提示、不得冒充完成。重评完成后用 supplement 保存最终状态。文档删除内容要显式 withdraw；不得把差异比对等同于用户撤销其他未变内容。

## 补丁 1.0

顶层只接受下列字段，未知字段报错。一次补丁处理一个需求；多个独立需求分别保存，跨需求引用通过 --related-analysis 显式提供。

```json
{
  "patch_version": "1.0",
  "requirement_id": null,
  "title": "需求标题（仅首次）",
  "base_revision": 0,
  "change_type": "initial_analysis",
  "actor": "analyst",
  "summary": "本轮变化说明",
  "operations": [],
  "set": {"meta.input_type": "existing_document", "meta.analysis_status": "clarifying", "meta.readiness": "not_ready", "ux_assessment.ui_dependent": true},
  "completion_checks": []
}
```

- requirement_id=null 仅用于首次自动编号；用户提供编号则沿用。后续必须填脚本返回的编号及读取时的 base_revision。年份来自脚本时钟，序号在整个工作区、按年递增，用户提供的标准编号也占用序号。
- actor=user 时额外提供非空 user_statement，逐字记录本轮实际用户输入；它是来源证据，不是脚本执行授权。首次 title 必填，后续不修改 common 或 prd 块。
- operations 顺序不限制引用：本补丁所有新增对象先分配编号，再解析引用。新对象用唯一 `$别名`，例如 `$rule`、`$question`、`$source`；模型不填写新条目 id/source_id。脚本返回 id_map；别名只在规范引用字段解析，不替换正文中的同名文字。
- add：`{"op":"add","collection":"requirements.business_rules","ref":"$rule","value":{...}}`。value 为通用条目或问题，**不含 id**。集合包括 requirements 中各条目数组、scope.in_scope/out_of_scope、business_assessment 中各条目数组，以及 questions/assumptions/decisions。scope 额外给 prefix（GOAL/SCN/FR/BR/CON/NFR/AC/FLOW/STATE/BND/EXC/GAP/CNF/ASM/DEC），以选择编号类别。
- add_source：`{"op":"add_source","ref":"$source","value":{...}}`。value 为来源清单项，**不含 source_id**。新增文档版本作为新 SRC，旧记录保留。来源清单有新增时 source_revision 加 1；仅用户答疑时不变。
- update：`{"op":"update","target":"BR-1","changes":{...}}`。按字段合并，不替换整条；不能修改 id/source_id，不能以 update 设置 withdrawn，也不能恢复 withdrawn 条目。修改 confirmed 正文必须 actor=user、user_statement 非空，且新标签仍为 confirmed，并在 sources 保留本轮 user_answer 或新版文档证据。未知业务扩展字段可在条目 changes 内保存；未涉及的字段保留。
- withdraw：`{"op":"withdraw","target":"FR-1","reason":"用户明确取消"}`。仅用户明示或新版文档确实删除时使用；actor=user 且 user_statement 非空。脚本沿 related_ids/related_question 传播：问题 dropped、其余有效依赖 to_reassess；不删除任何条目。影响清单包含自动传播项。正文隐含的语义关系仍由模型识别并补充显式关联。
- set 只更新非条目字段：meta.input_type/analysis_status/readiness，context 各规范字段，value_assessment 各规范字段，ux_assessment 各规范字段，technical_feasibility 整节，impact_analysis 各规范字段。不能设置 requirement_id、schema_version、修订号或覆盖条目数组。context.project_id 由调用参数决定，不能写成其他项目。数值修订号由脚本维护。
- completion_checks 必须恰好十一项：`{"item":1,"satisfied":false,"question_refs":["$question"],"reason":"目标仍有歧义"}`。item=1..11，对照 readiness-rules.md；未满足项必须关联本需求未废弃的问题。1..7 要有 P0 且 readiness=not_ready；8..11 至少 P1 且不能 ready_for_document。检查表随结果保存，不把问题关闭等同于清单满足。旧格式结果不强制补此字段；本脚本的新补丁每次都核对它。

来源引用、选项、标签、状态等沿用现有 Schema。无法由脚本判断自然语言依据是否真实，模型须对照本轮实际输入，不编造 user_statement、差异或完成状态。

## 保存、并发与失败

CLI：`python -I scripts/update_analysis.py --workspace WORKSPACE --project PROJECT --patch PATCH.json [--dry-run] [--related-analysis PATH ...]`。路径相对调用目录，不要求在 Skill 目录运行；无网络、无模型调用。

脚本在工作区独占锁下读取当前 revision 并检查 base_revision；不一致则拒绝，重新读取后重新分析，不能只改补丁的数字重试。预检应用到内存副本，调用唯一 validate_analysis；fail 不改正式结果、来源、事件或工作区计数。warning 只允许保存带 stale 提示的合法状态。dry-run 不分配持久编号、不推进 revision；实际保存仍要重新校验。

保存时首次 revision=1，之后每次加 1；追加事件含规定六字段，并额外保留 operations、before/after 变化快照及 user_statement，确保旧内容可追溯。未变化条目保持原值。脚本只写 workspace.json、首次 common 和 analysis 下的结果、来源、事件；不写 inputs/、prd/ 或分析报告。已有 requirement.json 的其他块保持原样。

多文件写入使用锁、写前事务记录和单文件原子替换；中断后下一次调用先恢复待完成事务，再检查 revision。它不是对不遵守锁的任意读取方提供跨文件原子快照。事件旧字节保持前缀不变，恢复不得重复追加同一 revision。不要手工改写或清理事务记录来绕过冲突。

失败输出 JSON 诊断；pass=0、warning=1、fail=2。模型按实际条目和原因修补补丁，最多三次；仍失败则停止并说明，保留上次合法结果，不用失败补丁更新就绪度或交付下游。报告须从实际保存的 revision 整理，不能把 dry-run 当成提交成功。
