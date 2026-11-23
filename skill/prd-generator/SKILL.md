---
name: prd-generator
description: 根据需求分析生成、同步或编辑可追溯 PRD，查看遗留事项并处理手工修改；用于提交或退回评审、检查发布条件、确认发布、查看已发布基线或废弃需求。
---

# PRD 生成、同步与发布

以需求分析为权威生成、维护和定稿 PRD。需求内容修改或含义不明的改动交回 Requirement Analyst；生成侧不调用分析写入器。

用 Skill 所属项目的虚拟环境运行脚本：Windows PowerShell 用本机 `.claude/.prd-skills-venv/Scripts/python.exe`（无需 WSL），macOS/Linux 用 `.claude/.prd-skills-venv/bin/python`。加 `-I -B`，传入脚本绝对路径；自备环境须已安装分析侧 `scripts/requirements.txt`。使用本地工作区，同一工作区只在一个系统下写入。

## 流程

1. 确定已有需求目录和可选项目模板。没有需求目录或分析结果时建议先做需求分析，不创建需求。仅以 `analysis/analysis-result.json` 为业务权威；不读人用分析报告，不写 `analysis/`。跨需求分析只接受用户显式提供的路径。
2. **评审、发布、查看基线或废弃**：读 [评审发布规则](references/versioning-and-release.md)，先运行对应的 `snapshot_release.py` 只读检查，包括待同步状态。发布仅在全项门禁通过并收到产品经理对本送审稿的明示确认后执行；同版退回重提也须重新确认。只读查看不写。生命周期操作在此分支结束，不继续首稿或同步。
3. 其他请求读 [门禁和降级](references/gating-rules.md)。首稿运行 `check_gate.py`；操作已有 PRD 前读 [同步规则](references/sync-rules.md)，用只读 `check_sync.py` 检查门禁及待同步。展示全部诊断，失败即停止；过期先建议重评，用户明确坚持后才允许过期草稿。
4. **编辑或检测到手改时**，读 [修改分流](references/numbering-and-trace.md)，用 `write_draft.py --inspect-edits` 查看整篇差异。内容性或无法判断的请求只回交；排版需逐项核对含义，用户明确坚持保留内容变化才标注不一致。只读查看不记录事件。若同时待同步，先处理手改，再由分析侧更正并同步；排版不前移分析基准。编辑后直接检查保存结果，不继续首稿。
5. **同步**：以旧稿为基础，只改受影响内容，未变条目保留原字节和编号。核实每个缺口的唯一接收问题与实际内容，充分才关闭；已有不一致也须依据核实。用 `write_draft.py --sync` 保存后直接检查结果。发布后同步或排版按 [版本规则](references/versioning-and-release.md)另建工作稿，旧快照保持不动。
6. **首稿或首次发布前重复生成**：读 [内容生成](references/generation-rules.md)、[章节结构](references/prd-structure.md) 和 [编号追溯](references/numbering-and-trace.md)。按有效分析构造正文、遗留事项和确有需要的缺口；模板必需而分析缺失的内容占位登记。用独立映射补丁调用 `assign_ids.py` 获取候选编号，不自编正式编号。
7. 首稿按 `templates/prd.md` 构造带定位标记的候选，以 `write_draft.py REQUIREMENT_DIR --patch PATCH.json --body CANDIDATE.md --candidate-dir NEW_DIRECTORY` 统一保存，可选 `--gaps GAP_REQUESTS.json`。候选目录须位于需求及关联分析目录外且不存在。
8. **检查保存结果**：展示警告；并发变化则重读。失败保留候选和诊断，连续三次修正仍失败即停止。中断按实际响应使用 `write_draft.py --recover`。成功时说明工作稿、实际变化、遗留事项与缺口处理，不把保存或查看称为已评审、已发布或已同步。

编号、摘要及格式以相应脚本和生成规格为准；机器校验不代替语义忠实性、缺口充分性及未标记文本的人工审查。变更摘要使用 [模板](templates/change-summary.md)，只记录实际变化。
