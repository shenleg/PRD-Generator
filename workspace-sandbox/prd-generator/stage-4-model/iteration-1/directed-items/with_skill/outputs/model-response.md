# 本次试跑结果：partial

私有 trial：`/home/collin/orca/PRD-Generator/workspace-sandbox/prd-generator/stage-4-model/iteration-1/directed-items/with_skill`

按协调要求收束，不再执行同步、补充检查或重跑。以下 generated/written 专指本次是否生成并保存同步结果，不包括复制旧产物和保存运行记录。

| 场景 | 状态 | generated | written | 实况与阻塞原因 |
| --- | --- | --- | --- | --- |
| PG-14 | partial | false | false | check_sync 通过；FR-1 为 modified，FR-2 为 unchanged。已阅读权威分析与旧稿，候选补丁 Write 被工作树隔离拒绝，未构造完整候选或调用统一保存。 |
| PG-16 | partial | false | false | check_sync 通过；新增 FR-3，既有 FR-1 已 abolished，FR-2 未变。候选补丁 Write 被工作树隔离拒绝；未调用 assign_ids 分配新号，未调用统一保存。 |
| PG-32-tag | partial | false | false | check_sync 通过；FR-1 标签改为 inferred，FR-2 未变。候选补丁 Write 被工作树隔离拒绝；【推断】及待验证说明尚未写入，未调用统一保存。 |

## 缺口与警告

三个场景的 gap-requests.json 均为 requests: []，没有关闭、补足或新增缺口。未把门禁通过视为人工批准。三个场景均为 formal_draft，未覆盖 value_assessment、technical_feasibility、impact_analysis。没有发布、安装、Git 操作，没有修改 analysis、冻结源码或其他元数据块。

## 已保存内容

- `artifacts/PG-14-check-sync.json`、`artifacts/PG-16-check-sync.json`、`artifacts/PG-32-tag-check-sync.json`：实际门禁与差异响应；对应 stderr 文件同时保留。
- `artifacts/assign-ids-help.txt`、`artifacts/write-draft-help.txt`：生产工具帮助响应；仅获取帮助，不代表编号或保存已执行。
- `artifacts/before/`：三个场景同步前输入快照。
- `artifacts/analysis-before.sha256`：同步前分析文件摘要；未执行事后验证，不宣称完成摘要对比。
- `artifacts/write-rejections.txt`：三次 Write 拒绝响应及执行上下文说明。
- `outputs/PG-14/`、`outputs/PG-16/`、`outputs/PG-32-tag/`：各自现存旧 PRD、trace、gap 的副本，**不是同步完成的结果**。版本仍为 0.1、基于分析修订 1。

阻塞为当时工具仅允许写隔离工作树副本，而任务指定只写共享 checkout 下的 run；没有改用其他写入手段绕过。收到环境更新后仅保存本说明、拒绝记录和既有产物副本，不恢复同步。
