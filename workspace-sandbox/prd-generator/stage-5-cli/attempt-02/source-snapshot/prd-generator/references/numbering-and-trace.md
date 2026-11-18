# 编号、追溯与修改分流

模型提交独立的 `patch_version: "1.0"` 映射补丁，含 `requirement_id`、读取时的 `base_prd_version`（初次无 PRD 为 `null`）、`base_analysis_revision`、`items`。每项含稳定唯一 `mapping_key`、`kind` 和非空不重复的完整 `analysis_refs`；可选 `prd_id` 仅定位已分配条目，不能指定新号。旧追溯无键时显式定位已有编号，歧义拒绝；不得提交计数器、摘要或正文。补丁与正文、缺口材料分离。

`assign_ids.py` 分配 `PRD-<分析前缀>-<至少三位序号>`，不截断大序号；同需求唯一，保持既有映射，不重排、不复用。种类为 `goal`、`scenario`、`functional_requirement`、`business_rule`、`constraint`、`non_functional_requirement`、`acceptance_criterion`、`flow`、`state`、`boundary`、`exception`。遗留问题、假设、决策、矛盾、缺口沿用分析编号。跨需求资料必须显式提供，引用始终写 `需求编号/分析条目编号`。

脚本默认输出追溯候选，`--write` 才独立写入追溯；首稿及显式 `--sync` 同步均由 `write_draft.py` 统一保存，已有待同步工作稿不能独立改追溯。同步先读 [同步规则](sync-rules.md)，参数以各脚本帮助为准。每个正式条目均有完整来源；一对多使用不同映射键，多对一保留全部来源并取最不确定标签。`source_digest` 对按完整引用排序的 `{"analysis_ref": ..., "item": ...}` 数组以排序键、紧凑分隔、UTF-8、不转义正常 Unicode、拒绝非有限数值的 JSON 计算 SHA-256；保留数组顺序。正文 `content_hash` 是 Markdown 原始字节摘要，不可混用。

## 修改分流与手改处理（阶段 5 实施中，待验收）

需求点、规则、范围、验收或优先级的修改回交分析；可能改变含义或无法判断的措辞也按内容修改处理，只建议交接、不写正文或事件，不调用分析写入器。先运行只读 `check_sync.py DIR` 检查门禁、待同步及 `manual_edits`；所有操作均先查待同步。存在手改时先处理手改，再由分析侧更正并同步，编辑不前移分析基准，不能绕过分析门禁。

只读 `write_draft.py DIR --inspect-edits [--previous-body OLD.md]` 输出实际摘要、预期摘要、`diff`、`baseline_available`、`changed`，不写事件。比较覆盖整篇原始正文，包括非编号章节及未标记文本；模型逐差异核对含义，人工评审语义，格式检查不能证明含义不变。`meta.content_baseline` 为上次统一保存的 UTF-8 原始正文，其 SHA-256 必须等于 `content_hash`；不归一化换行。旧稿缺基准但当前正文与摘要一致时可在下一次合法保存建立；已手改且缺基准须用 `--previous-body` 提供摘要匹配的真实旧正文，不可用重生成内容伪造基准。

显式处理通过既有统一写入器，只接受未发布工作稿：

```text
write_draft.py DIR --edit layout|detect|keep --base-prd-version VERSION --base-analysis-revision N --base-content-hash SHA --edit-summary TEXT [--body CANDIDATE.md] [--meaning-reviewed] [--keep-confirmed] [--previous-body OLD.md] [--candidate-dir NEW]
```

- 所有输入绑定读取时的 PRD 版本、分析修订和**当前正文**原始字节摘要，而不是追溯中可能过期的摘要；提交前重新检查待写文件及输入，冲突重读。候选由脚本渲染 `info`、`changes`，校验后统一保存；保留编号、引用、来源摘要、计数器、缺口内容及交接状态。
- `layout` 必须提供 `--body` 和 `--meaning-reviewed`，后者表示模型已逐差异核对含义；首次发布前次版本递增并记录 `layout_edit`。确认标志不是程序对语义的证明。
- `detect` 不带正文及上述确认，只在用户明确授权处理检测事件时使用；追加 `manual_edit_detected`，不递增版本、不刷新原摘要、不撤销手改。查看差异本身不授权记录事件。
- `keep` 必须提供 `--body` 和 `--keep-confirmed`，仅对应真实用户收到内容性差异说明后坚持保留；首次发布前次版本递增，记录处理。该标志不能代替用户回答。

坚持保留时，在原内容位置和 `residuals` 遗留项中成对标注【与分析不一致】，遗留项解释差异及回交建议；只增加标注和说明，保留用户实际手改及既有实质遗留项。新增遗留项后，原有独立“无适用遗留项”等空集合提示允许并由脚本移除，避免文档自相矛盾。正式条目的遗留块使用 `<!-- prd:residual REQ-2026-001/PRD-FR-001 -->`；非编号内容使用 `<!-- prd:residual REQ-2026-001/prd/sections/<section_key> -->`，对应实际内容章节，不指向 `info`、`changes`、`residuals`；以 `<!-- /prd:residual -->` 结束。未发布稿成对不一致为明确“不得发布”的 `warning`；不配对、目标不存在或已发布产物含不一致为 `fail`。完整 `PG-19` 发布拒绝仍属阶段 6。

排版和同输入重复生成不得抹去既有不一致；同步仅在核对分析确实覆盖该变化后清除，修订递增、摘要一致或问题状态改变均不够。脚本不证明自然语言忠实，也不把分析交接当成缺口关闭。
