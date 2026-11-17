# 编号、追溯与修改分流

模型提交独立的 `patch_version: "1.0"` 映射补丁，含 `requirement_id`、读取时的 `base_prd_version`（初次无 PRD 为 `null`）、`base_analysis_revision`、`items`。每项含稳定唯一 `mapping_key`、`kind` 和非空不重复的完整 `analysis_refs`；可选 `prd_id` 仅定位已分配条目，不能指定新号。旧追溯无键时显式定位已有编号，歧义拒绝；不得提交计数器、摘要或正文。补丁与正文、缺口材料分离。

`assign_ids.py` 分配 `PRD-<分析前缀>-<至少三位序号>`，不截断大序号；同需求唯一，保持既有映射，不重排、不复用。种类为 `goal`、`scenario`、`functional_requirement`、`business_rule`、`constraint`、`non_functional_requirement`、`acceptance_criterion`、`flow`、`state`、`boundary`、`exception`。遗留问题、假设、决策、矛盾、缺口沿用分析编号。跨需求资料必须显式提供，引用始终写 `需求编号/分析条目编号`。

脚本默认输出追溯候选，`--write` 才独立写入追溯；首稿及显式 `--sync` 同步均由 `write_draft.py` 统一保存，已有待同步工作稿不能独立改追溯。同步先读 [同步规则](sync-rules.md)，参数以各脚本帮助为准。每个正式条目均有完整来源；一对多使用不同映射键，多对一保留全部来源并取最不确定标签。`source_digest` 对按完整引用排序的 `{"analysis_ref": ..., "item": ...}` 数组以排序键、紧凑分隔、UTF-8、不转义正常 Unicode、拒绝非有限数值的 JSON 计算 SHA-256；保留数组顺序。正文 `content_hash` 是 Markdown 原始字节摘要，不可混用。

需求点、规则、范围、验收或优先级的修改回到需求分析；可能改变含义的措辞也按内容修改处理。纯排版修改在当前阶段尚未实现，说明能力边界，不直接改稿。不要调用分析写入器。
