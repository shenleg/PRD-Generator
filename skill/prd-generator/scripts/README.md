# PRD 生成与同步脚本

本目录实现门禁、编号、信息渲染、草稿生成、增量同步、编辑、评审、发布及废弃。阶段验收以实际运行和人工记录为准；测试确认只适用于隔离的合成工作区。

## 依赖与安装边界

- Python 3.10+，使用并列 `requirement-analyst/scripts/requirements.txt` 的依赖；两个 Skill 必须一起安装。
- 分析校验器从相邻生产目录加载，不复制分析规则，不依赖仓库测试和最小消费者。脚本支持隔离模式及任意调用目录。
- 当前针对可信 Linux/Unix 本地工作区。共享需求目录锁串行化同一需求的生成侧写入、分析提交和恢复、缺口接收标记；不承诺不遵守此锁的写入方、不同需求间引用或网络文件系统的跨文件原子性。
- 工作区必须由分析侧已有的 `requirement.json/common` 和 `analysis/analysis-result.json` 开始；生成侧不创建需求，不读取 `analysis-report.md`，不写 `analysis/`。

以下命令中的 `PY` 表示：

```bash
uv run --offline --no-project --python /usr/bin/python3 \
  --with-requirements skill/requirement-analyst/scripts/requirements.txt python -I -B
```

## 首稿顺序

### 1. 只读门禁

```text
PY skill/prd-generator/scripts/check_gate.py REQUIREMENT_DIR
```

可选 `--related-analysis PATH` 可重复，仅使用显式关联资料；`--allow-stale` 只在用户已听到过期提示并明确坚持后使用，不能替用户同意。输出单个 JSON，包含 `status`、`diagnostics`、`allowed`、`draft_kind` 及读取上下文。`warning` 与是否允许继续分开：过期且未获坚持时 `allowed=false`，不得因退出码只是警告而继续。

### 2. 编号候选

模型根据分析和模板提出独立映射补丁，格式沿用 `schemas/numbering-patch.schema.json`。首次 `base_prd_version=null`，重复生成携带实际读取的版本；模型不提交新正式编号、计数器、摘要或正文。

```text
PY skill/prd-generator/scripts/assign_ids.py REQUIREMENT_DIR --patch PATCH.json
```

默认只输出追溯候选，不写任何文件。候选 `meta.content_hash` 暂为空正文摘要，**不能把它当作最终追溯直接保存**。模型用返回编号写候选正文，正式编号和完整引用放入稳定条目块；功能和验收表格带分析来源列。

`--write` 是仅限未发布首稿的独立追溯维护接口，复用分析门禁及目录锁、读时版本和原字节检查；发现正文摘要变化则拒写，不把尚未判断的手工改动重置成合法摘要。已有正文时只允许幂等维护或给旧追溯身份补键；待同步、增拆编号、来源摘要或标签变化必须走相应的完整保存流程，不能先独立刷新追溯。不负责正文、事件或元数据；完整草稿使用下一步统一保存，不先独立写正式追溯。未完成统一事务、评审/发布/废弃状态或已有发布快照均拒绝独立写入。

### 3. 统一校验与保存

```text
PY skill/prd-generator/scripts/write_draft.py REQUIREMENT_DIR \
  --patch PATCH.json --body CANDIDATE.md \
  --candidate-dir NEW_DIRECTORY_OUTSIDE_REQUIREMENT
```

可选 `--gaps GAP_REQUESTS.json` 提供完整版本化缺口候选；缺省首次为空，重复生成沿用当前缺口。默认首稿模式只新增 `open` 请求，不删除、不重置交接进度或关闭缺口；关闭仅在显式同步中按现有协议核实。`--related-analysis PATH`、`--allow-stale` 语义与门禁相同。

写入器重新执行门禁，复用编号和信息渲染，校验完整候选后才保存。首次版本 `0.1`，同一分析输入重复生成次号递增；需求正文及编号应稳定，文档信息和事件依版本变化。分析修订已变化时拒绝整篇重生成，转入显式增量同步；有手工修改、旧整数版本、已发布状态或快照时不自动迁移或覆盖。

- 候选目录必须不存在、位于正式需求目录外；未指定则在系统临时目录新建，响应返回位置。候选可能包含分析副本，应按业务资料管理，不公开上传。
- `render_info.py` 根据元数据替换信息视图与草稿提示，计算正文原始字节摘要；写入器生成事件和变更记录。不会改写模型的需求正文。
- 正式保存只更新本需求的正文、追溯、缺口、`prd` 块并追加事件，保留 `common` 和其他扩展。
- 写前核对目标原字节、读时版本及分析修订；发现并发变化拒绝，不盲改基准数字重试。
- 候选校验失败保留候选和诊断，不触碰正式产物，不宣布完成；预期警告完整展示。连续修正三次仍失败停止，由 Skill 负责记录次数。

### 4. 中断恢复与最终检查

```text
PY skill/prd-generator/scripts/write_draft.py REQUIREMENT_DIR --recover
PY skill/prd-generator/scripts/validate_prd.py REQUIREMENT_DIR
```

跨文件保存中断时，响应 `fail` 并保留 `prd/.prd-transaction.json`，不报告完整成功。新生成和独立编号写入暂停，显式恢复仅在原分析/来源及目标文件仍符合该事务的读前或写后快照时向前完成；不会重复事件。冲突时保留记录和候选，不覆盖新内容，不自动删除冲突文件。

这是生成侧私有运行恢复记录，不是新的业务交换协议，不写入分析事务。恢复后仍须检查真实响应和最终文件；未完成事务不作为合法草稿交付。

## 显式增量同步

每次操作已有 PRD 前先运行只读比较：

```text
PY skill/prd-generator/scripts/check_sync.py REQUIREMENT_DIR
```

输出 `pending`、`based_on_analysis_revision`、当前 `analysis_revision`、既有正式条目的 `items`（`unchanged/modified/withdrawn/to_reassess`）及本需求未映射的 `added` 来源。`source_digest` 覆盖完整分析条目；只改标签、来源、关联也能发现，键顺序和 JSON 排版不触发条目重写。只有修订递增时仍可待同步，但正式条目差异为空。跨需求文档只为显式引用提供依据，不自动导入其功能；范围依据不误当新增功能。

按 [同步规则](../references/sync-rules.md) 以旧稿定向构造完整候选，未变正式条目连同标记保留原始字节及章节。通过只读编号候选取得新号，旧映射可由保存入口补齐重算；不以独立 `--write` 更新待同步稿。

```text
PY skill/prd-generator/scripts/write_draft.py REQUIREMENT_DIR --sync \
  --patch PATCH.json --body CANDIDATE.md --gaps GAP_REQUESTS.json \
  --candidate-dir NEW_DIRECTORY_OUTSIDE_REQUIREMENT
```

`--gaps` 可省略以保留当前请求。显式同步要求分析修订高于原基准，产生新工作稿，状态回到 `draft`。首发前次版本递增；首发后按[版本规则](../references/versioning-and-release.md#工作稿版本与基线)另建或递增工作稿。撤销保留编号及事件记录；待重评保留标注；新增不复用编号。未变条目改写、遗漏新增映射、替换既有分析身份、手工修改未处理和并发目标变化均拒写。

关闭缺口须提交完整缺口候选中的 `closed` 与既有 `resolution`，唯一接收问题非 `open`，引用当前有效、有内容的分析依据；`not_needed` 须引用决策或范围依据。脚本不能仅凭状态判定补足；模型与人工须核对所需内容充分性。未提交核实依据则保留请求和占位；暂定补足仍保留标注及遗留事项。禁止改写缺口描述、扩展或伪造 `handed_over`。

统一保存记录兼容选填的 `meta.section_source_digests`，依据未变的整章也须保持原字节，补足对范围等非编号内容的保护。旧追溯缺字段时可用 `--previous-analysis OLD_ANALYSIS.json` 指定与旧基准身份/修订匹配的分析；缺可信旧依据时输出明确警告，须人工逐章核对，不能冒称已自动证明全篇最小化。成功后建立当前章节依据。功能、规则等保持对应稳定键，验收仅按显式 `related_ids` 挂靠功能。

同步共用上述候选、并发及恢复机制，事件类型为 `sync`；变更记录包含四类受影响编号、就绪度和遗留事项变化。辅助事件缺失只按条目汇总，来源清单缺失只显示 `source_id`，降级写入信息且完整输出警告。`check_sync.py` 始终只读。

## 显式编辑与手改检测

每次操作先用 `check_sync.py` 检查待同步及只读 `manual_edits` 比较；发现手改先处理，再由分析侧更正并同步，不能用编辑前移分析基准。

```text
PY skill/prd-generator/scripts/write_draft.py REQUIREMENT_DIR --inspect-edits [--previous-body OLD.md]
PY skill/prd-generator/scripts/write_draft.py REQUIREMENT_DIR --edit layout|detect|keep \
  --base-prd-version VERSION --base-analysis-revision N --base-content-hash SHA \
  --edit-summary TEXT [--body CANDIDATE.md] [--meaning-reviewed] [--keep-confirmed] \
  [--previous-body OLD.md] [--candidate-dir NEW_DIRECTORY_OUTSIDE_REQUIREMENT]
```

查看输出实际摘要、预期摘要、`diff`、`baseline_available`、`changed`，不写事件。编辑基准摘要绑定读取时当前正文原始字节，不能使用可能过时的追溯摘要；版本、分析修订和待写文件均需重新核对。`layout` 需要正文及模型逐差异核对后提供的 `--meaning-reviewed`；`detect` 不带正文和确认标志，只在明确授权处理时追加事件，不递增版本、不刷新旧摘要；`keep` 需要正文及用户实际坚持后的 `--keep-confirmed`。标志本身不证明语义或用户意愿。候选的信息和变更记录由脚本渲染；编号、引用、来源摘要、计数器、缺口内容与交接状态保持。

正文基准缺失且旧稿已手改时须提供摘要匹配的真实旧正文，不能伪造。尚未改稿的内容性或无法判断请求只建议回交分析，不写正文或事件。成对不一致为明确不得发布的警告，不成对为失败；已有不一致不得因排版、重复生成或未经核实的同步清除。新增手工不一致遗留项后，写入器允许并移除遗留章内独立的“无适用遗留项”等空集合提示，不借此删改真实遗留说明。具体分流、定位及基准见 [修改分流](../references/numbering-and-trace.md)；发布后的排版另建或递增工作稿，不动旧快照。

## 评审、发布和废弃

```text
PY skill/prd-generator/scripts/snapshot_release.py DIR check --for-action submit-review
PY skill/prd-generator/scripts/snapshot_release.py DIR submit-review --binding VALUE_FROM_CHECK
PY skill/prd-generator/scripts/snapshot_release.py DIR check
PY skill/prd-generator/scripts/snapshot_release.py DIR release --binding VALUE_FROM_CHECK \
  --confirmed-by PM_NAME --confirmed-at ISO_TIMESTAMP_WITH_TIMEZONE
```

`check` 只读，默认检查 `release`。也可指定 `--for-action return-review` 或 `deprecate` 后以同名操作和检查绑定写入；`deprecate` 同样需要实际产品经理确认人和确认时间。任何操作的检查绑定不能用于其他操作或版本。可重复传入显式 `--related-analysis`，写入可用 `--candidate-dir` 保留新候选。

将检查列出的实际版本和分析修订展示给产品经理；实际确认后才提交发布参数。看 `applied` 和 `written` 判断写入，`baseline_version` 与 `baseline_verified` 区别待定稿和已经验证的最新快照；若已废弃，最后基线只作为历史资料。失败报告具体原因，不重用旧确认。若 `recovery_required: true`，先用 `write_draft.py DIR --recover` 完成原事务，不重复执行发布。

两份快照以只读权限独占新建，日志记录原始字节摘要。仅实际发布可创建快照；生成、同步、编辑和退回不修改旧基线。详情见[发布门禁](../references/versioning-and-release.md#发布门禁)。

## 单独渲染信息

```text
PY skill/prd-generator/scripts/render_info.py REQUIREMENT_DIR \
  --body CANDIDATE.md --trace CANDIDATE_TRACE.json
```

输出 JSON 中的 `markdown`、`content_hash`，不保存正式业务文件。可选 `--generated-at` 固定展示时间，`--uncovered` 可重复指定降级项；统一保存时从门禁和当前输入重新获取权威上下文，不依赖手工填写的信息表。

## 只读校验

`validate_prd.py REQUIREMENT_DIR` 检查生成规格 §9.9 的十二条规则。可选：

| 参数 | 用途 |
| --- | --- |
| `--related-analysis PATH` | 显式跨需求分析，可重复，不扫描工作区 |
| `--previous-trace PATH` | 核对历史编号、高水位及稳定身份；没有历史不宣称证明从未复用 |
| `--numbering-patch PATH` | 对已有工作稿附加只读映射补丁检查，不分配编号 |

来源清单缺失或不可读时复用上游适用检查并显式警告，来源只显示 `source_id`，不把未核验来源当作完整上游通过。旧追溯没有 `mapping_key` 仍可读，显式按旧编号补键不重编号；已有键不可被重置。快照摘要按原始字节核对；若存在未完成事务，先恢复再校验，不把部分落盘当成有效发布。

## 结果边界

门禁、写入及只读校验输出 `pass/warning/fail`，退出码分别为 `0/1/2`；门禁还须检查 `allowed`，写入还须检查实际 `generated/written`。编号候选成功输出追溯，错误输出失败 JSON。诊断保留规则、条目、位置和原因；业务文件、候选失败、恢复未完成不混称。

程序通过说明已执行的结构和一致性检查通过，不证明自然语言忠实性、缺口必要性或实际内容充分；两组业务参考及人工草稿试用仍是阶段退出条件。所有候选、测试时间和合成确认不代表发布授权。
