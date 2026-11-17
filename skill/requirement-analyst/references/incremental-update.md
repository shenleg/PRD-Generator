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

裁决或采用暂定方案后，旧原文仍是可追溯证据，但被否定或被假设暂代的候选规则不再是当前有效规则：保留正文与来源并标 to_reassess，当前方案单独保留 confirmed 或 assumption；不能只关闭 CNF/Q，却让互斥规则继续同时 active。用户明示撤销才使用 withdraw，避免把已回答问题也误废弃。

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
- update：`{"op":"update","target":"BR-1","changes":{...}}`。按字段合并，不替换整条；不能修改 id/source_id，不能以 update 设置 withdrawn，也不能恢复 withdrawn 条目。修改 confirmed 正文必须 actor=user、user_statement 非空，且新标签仍为 confirmed，并在 sources 保留本轮 user_answer 或本补丁新增 input_document/project_material 来源证据。未知业务扩展字段可在条目 changes 内保存；未涉及的字段保留。
- withdraw：`{"op":"withdraw","target":"FR-1","reason":"用户明确取消"}`。仅用户明示或新版文档确实删除时使用；actor=user 且 user_statement 非空。脚本沿 related_ids/related_question 传播：问题 dropped、其余有效依赖 to_reassess；不删除任何条目。影响清单包含自动传播项。正文隐含的语义关系仍由模型识别并补充显式关联。
- set 只更新非条目字段：meta.input_type/analysis_status/readiness，context 各规范字段，value_assessment 各规范字段，ux_assessment 各规范字段，technical_feasibility 整节，impact_analysis 各规范字段。不能设置 requirement_id、schema_version、analysis_revision/source_revision 或覆盖条目数组。context.project_id 由调用参数决定，不能写成其他项目。analysis/source修订号由脚本维护。阶段5另允许set context.history_review，以及用户明确确认时设置/解除meta.baseline_revision；采用来源、发布依据、别名与一致性见 historical-retrieval.md，检索不能自动宣布某资料为现行基线。
- completion_checks 必须恰好十一项：`{"item":1,"satisfied":false,"question_refs":["$question"],"reason":"目标仍有歧义"}`。item=1..11，对照 readiness-rules.md；未满足项必须关联本需求未废弃的问题。1..7 要有 P0 且 readiness=not_ready；8..11 至少 P1 且不能 ready_for_document。检查表随结果保存，不把问题关闭等同于清单满足。旧格式结果不强制补此字段；本脚本的新补丁每次都核对它。

来源引用、选项、标签、状态等沿用现有 Schema。无法由脚本判断自然语言依据是否真实，模型须对照本轮实际输入，不编造 user_statement、差异或完成状态。

## 接收 PRD 缺口

收到生成侧回交或用户要求处理缺口时，读取本需求 `prd/gap-requests.json` 和最新分析；按本节生成 `supplement` 补丁，先登记问题，再按问题优先级进入澄清流程。缺口的描述是待确认信息，不是新的业务事实。

1. 核对版本化封装的 `schema_version`、`requirement_id`、`counters` 和 `requests`。逐项读取 `open` 缺口；中断重试也读取已保存的问题。跨需求引用只使用显式提供的 `--related-analysis`，不自动搜索工作区。
2. 按 `gap_request_ref: "GAPREQ-N"` 查重。同一缺口复用已有问题及其答案、优先级和进度；答疑或变更问题仍通过明确的 `update` 操作处理，不借重新交接覆盖。
3. 首次接收用已有 `add` 操作向 `questions` 新增问题，`value` 填 `gap_request_ref`，其余字段按问题 Schema 和问题策略填写。新编号由更新器分配，模型只给 `$别名`。接收关联不可转移至另一个缺口。
4. `related_analysis_refs` 必须是完整的 `需求编号/条目编号` 且引用存在。对应 `related_ids` 保持顺序，本需求去掉前缀，跨需求保留完整格式；也可把本需求完整引用交给更新器规范化。空数组保持为空，不额外臆造关联。候选引用不符时更新器拒绝保存。
5. 根据真实缺口判定优先级、责任方和就绪度，并核对十一项清单。运行更新器，读取实际响应及保存结果；只在分析事务成功后，由更新器把本次接收的 `open` 状态改为 `handed_over`。这只是接收确认，不表示内容已补足。

接收操作示例（嵌入完整补丁，不是独立补丁）：

```json
{"op":"add","collection":"questions","ref":"$gap_question","value":{
  "question":"请明确缺口中所需的规则？","priority":"P1","resolution":"ask_product",
  "reason":"PRD 对应章节缺少分析依据","impact":"影响规则与验收口径",
  "options":["补充规则","暂不确定","其他"],"recommendation":"先核对实际业务依据",
  "status":"open","related_ids":["FR-1"],"gap_request_ref":"GAPREQ-1"
}}
```

重复 `add` 会返回已有问题编号的 `id_map`，不覆盖候选与已有问题的差异。纯重复接收且其他分析内容未变时，不推进修订、不追加事件；`written=false` 不代表接收失败，应同时看 `status` 和实际缺口状态。首次接收以 `supplement` 事件记录。`closed` 保持关闭，不回退状态。

**失败恢复**：保存失败不标记缺口；若存在未完成分析事务，下次调用先按原事务恢复。分析已保存但状态标记失败时，响应为 `fail`，仍保留 `written=true` 和已保存的 `revision`；重新读取分析及缺口、重新判断并生成当前修订补丁，复用原问题继续标记。普通修订冲突同样拒绝，不能只改数字重试。`gap_status_written` 表示本次是否实际改了缺口状态，不表示缺口已解决。

标记阶段在需求目录上取得与生成侧相同的独占目录锁，再比较读取时的缺口原字节并替换；分析工作区锁本身不能阻止生成侧读后写覆盖。锁顺序为分析工作区锁后取得需求目录锁，生成侧不反向获取分析工作区锁。发生并发变化则保留生成侧最新文件并报告冲突。缺口文件不进入分析事务，避免恢复时重放过期的生成侧快照。分析侧对 `prd/` 的唯一写入例外是由更新器修改本次已保存接收问题对应的 `status`；保留其他缺口、计数器、关闭依据和未知扩展，不改正文、追溯或版本文件。关闭缺口由生成侧在同步时核实实际分析内容后处理。

## 保存、并发与失败

CLI：`python -I scripts/update_analysis.py --workspace WORKSPACE --project PROJECT --patch PATCH.json [--dry-run] [--related-analysis PATH ...]`。路径相对调用目录，不要求在 Skill 目录运行；无网络、无模型调用。

脚本在工作区独占锁下读取当前 revision 并检查 base_revision；不一致则拒绝，重新读取后重新分析，不能只改补丁的数字重试。预检应用到内存副本，调用唯一 validate_analysis；fail 不改正式结果、来源、事件或工作区计数。warning 只允许保存带 stale 提示的合法状态。dry-run 不分配持久编号、不推进 revision；实际保存仍要重新校验。

保存时首次 revision=1，之后每次加 1；追加事件含规定六字段，并额外保留 operations、before/after 变化快照及 user_statement，确保旧内容可追溯。未变化条目保持原值。脚本常规只写 workspace.json、首次 common 和 analysis 下的结果、来源、事件；接收缺口时仅另按上节修改 `prd/gap-requests.json` 对应状态。不写 inputs/ 或分析报告，不修改其他 prd/ 文件。已有 requirement.json 的其他块保持原样。

多文件写入使用锁、写前事务记录和单文件原子替换；中断后下一次调用先恢复待完成事务，再检查 revision。它不是对不遵守锁的任意读取方提供跨文件原子快照。事件旧字节保持前缀不变，恢复不得重复追加同一 revision。不要手工改写或清理事务记录来绕过冲突。

失败输出 JSON 诊断；pass=0、warning=1、fail=2。模型按实际条目和原因修补补丁，最多三次；仍失败则停止并说明，保留上次合法结果，不用失败补丁更新就绪度或交付下游。报告须从实际保存的 revision 整理，不能把 dry-run 当成提交成功。
