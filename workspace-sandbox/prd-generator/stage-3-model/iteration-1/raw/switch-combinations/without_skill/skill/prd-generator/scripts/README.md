# PRD 首稿脚本

本目录实现阶段 3 的门禁、正式编号、信息渲染及统一首稿保存，并保留阶段 1 的只读校验。同步、编辑分流、评审和发布仍未实现，不能以草稿或合成快照代替发布基线。

## 依赖与安装边界

- Python 3.10+，使用并列 `requirement-analyst/scripts/requirements.txt` 的依赖；两个 Skill 必须一起安装。
- 分析校验器从相邻生产目录加载，不复制分析规则，不依赖仓库测试和最小消费者。脚本支持隔离模式及任意调用目录。
- 当前针对可信 Linux/Unix 本地工作区，使用目录锁串行化合作的生成侧写入；不承诺恶意并发路径替换或网络文件系统的持久化安全。
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

`--write` 是独立追溯维护接口，使用目录锁、读时版本和原字节检查，但不负责正文、事件或元数据；完整草稿使用下一步统一保存，不先独立写正式追溯。存在未完成统一事务时独立写入拒绝。

### 3. 统一校验与保存

```text
PY skill/prd-generator/scripts/write_draft.py REQUIREMENT_DIR \
  --patch PATCH.json --body CANDIDATE.md \
  --candidate-dir NEW_DIRECTORY_OUTSIDE_REQUIREMENT
```

可选 `--gaps GAP_REQUESTS.json` 提供完整版本化缺口候选；缺省首次为空，重复生成沿用当前缺口。当前阶段只新增 `open` 请求，不删除、不重置交接进度或关闭缺口。`--related-analysis PATH`、`--allow-stale` 语义与门禁相同。

写入器重新执行门禁，复用编号和信息渲染，校验完整候选后才保存。首次版本 `0.1`，同一分析输入重复生成次号递增；需求正文及编号应稳定，文档信息和事件依版本变化。分析修订已变化时拒绝整篇重生成，转入后续同步能力；有手工修改、旧整数版本、已发布状态或快照时不自动迁移或覆盖。

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

来源清单缺失或不可读时复用上游适用检查并显式警告，来源只显示 `source_id`，不把未核验来源当作完整上游通过。旧追溯没有 `mapping_key` 仍可读，显式按旧编号补键不重编号；已有键不可被重置。快照摘要按原始字节核对，当前仍无真实发布入口。

## 结果边界

门禁、写入及只读校验输出 `pass/warning/fail`，退出码分别为 `0/1/2`；门禁还须检查 `allowed`，写入还须检查实际 `generated/written`。编号候选成功输出追溯，错误输出失败 JSON。诊断保留规则、条目、位置和原因；业务文件、候选失败、恢复未完成不混称。

程序通过说明已执行的结构和一致性检查通过，不证明自然语言忠实性、缺口必要性或实际内容充分；两组业务参考及人工草稿试用仍是阶段退出条件。所有候选、测试时间和合成确认不代表发布授权。
