---
name: prd-generator
description: 根据已校验的需求分析生成可追溯 PRD 首稿；也用于请求同步 PRD、查看遗留事项、提交评审或发布时说明当前能力边界。
---

# PRD 首稿生成

本 Skill 当前支持首次草稿和相同分析输入的重复生成。同步、编辑、提交评审、发布尚未实现；收到此类请求时明确告知，不模拟完成。查看遗留事项时只读取现有材料并说明其状态，不宣称已同步。需求内容修改或含义不明的改动交回 Requirement Analyst，由用户决定后续分析；不调用分析写入器。

## 流程

1. 确定已有需求目录和可选项目模板。没有需求目录或分析结果时建议先做需求分析，不创建需求。仅以 `analysis/analysis-result.json` 为业务权威；不读人用分析报告，不写 `analysis/`。跨需求分析只接受用户显式提供的路径。
2. 读取 [门禁和降级](references/gating-rules.md)，运行门禁并展示全部诊断。失败即停止；过期时先建议重新评估，只有用户明确坚持才允许过期草稿。记下读取时的版本、分析修订和待写文件状态。
3. 读取 [内容生成](references/generation-rules.md) 和 [章节结构](references/prd-structure.md)，按有效分析构造正文、遗留事项及确有必要的缺口；不以空的必有章节自动认定缺口。项目模板必需而分析缺失的信息必须占位并登记。
4. 读取 [编号和追溯](references/numbering-and-trace.md)，构造独立的映射补丁。调用 `assign_ids.py` 获取追溯候选，由脚本分配正式编号；默认不写入，`--write` 才独立写追溯。将正式编号填入候选正文，禁止自行编造编号。
5. 按 `templates/prd.md` 的结构及标记构造候选，由 `write_draft.py` 统一保存；它会调用 `render_info.py` 渲染权威信息，不必先手填或单独保存信息表。命令：`write_draft.py REQUIREMENT_DIR --patch PATCH.json --body CANDIDATE.md --candidate-dir NEW_DIRECTORY`；可选 `--gaps GAP_REQUESTS.json`。候选目录须在正式需求目录外且不存在，不用独立编号 `--write` 代替统一保存。
6. 保存前检查候选以及读时版本、分析修订和待写文件；并发变化则重读，不覆盖。展示所有警告；失败保留候选及诊断，不宣布完成。校验失败修正后重试，连续三次仍失败则停止并报告。成功后告知草稿类型、遗留事项、缺口和文件位置，不暗示评审或发布。

编号、追溯及文档校验以相应脚本和生成规格为准；机器检查不代替语义忠实性审查。需要变更摘要时参考 [模板](templates/change-summary.md)，不将其当作同步已实现。
