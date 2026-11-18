# PRD 候选模板

本文件是编写指引，不是可直接保存的工作稿。选择与门禁结果一致的文首提示；文档信息由 `render_info.py` 渲染，章节与机器标记遵循 `references/prd-structure.md`。仅插入适用的可选章节，必要章节空时写“分析结果中无此项”。占位符不是业务事实，也不是默认缺口。

```markdown
<对应草稿提示>

<!-- prd:section info -->
# 文档信息
<脚本渲染的信息表>
<!-- /prd:section -->

<!-- prd:section changes -->
# 变更记录
<实际生成事件>
<!-- /prd:section -->

<按默认顺序插入适用章节；每节使用稳定 section 键>

<!-- prd:section functional_requirements -->
# 功能需求
| 编号 | 内容 | 分析来源 |
| --- | --- | --- |
| <!-- prd:item <脚本分配的编号> --><编号> | <带适用标注的内容> | <完整分析引用><!-- /prd:item --> |
<!-- /prd:section -->

<!-- prd:section residuals -->
# 遗留事项
<!-- prd:residual <完整分析引用或设计事项指针> --><可追溯的遗留项><!-- /prd:residual -->
<!-- /prd:section -->
```

表格中的条目起止标记分别位于单元格内，块内包括可见编号、内容及完整来源；各正式条目及缺口按规格分别定位。验收条件同样使用带分析来源列的表格。确有缺口时每个请求只生成一个 `prd:gap` 块和“待分析补充”，并登记缺口。
