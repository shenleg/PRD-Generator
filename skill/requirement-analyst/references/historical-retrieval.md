# 历史资料对照与基线保护

本文件用于用户指定历史需求、项目资料检索、新旧规则重叠/冲突、正式基线变更，以及资料变化或老旧提醒。先定位依据，再做语义判断；脚本只提供机械候选，不替产品裁决。

## 检索与采用

1. 先读当前需求原文和现有分析，再读用户明确指定的相关资料；明确指定时不以自动检索替代用户意图。
2. 尚有缺口再查项目背景/规范、当前模块已发布需求、相关历史需求/变更、系统技术资料、其他项目资料。不要一次读全工作区。
3. 用户给出项目根和显式资料清单时，用 `index_sources.py --project-root ROOT --catalog CATALOG` 建索引；来源字段同source-manifest，附module/tags/terms/requirement_id和authority。当前发布/正式规范必须给publication_basis；文件名“正式”或mtime不代表已发布。
4. `search_project.py --project-root ROOT --query "关键词"` 默认最多5条、摘录总计2000字符；用--requirement/--module/--tag/--term筛选，--limit最多20、--max-chars最多20000。读取本身另限64份/2MiB，单文件1MiB。命中不足时换词或缩小范围；无命中、预算截断均不表示无关联或无冲突。
5. 模型只读取相关命中或手动指定资料的必要章节。每条保留source_id、path、location、revision、sha256、authority和credibility。索引来源编号只在该catalog内有效，导入本需求时用add_source分配新SRC，不能直接复用另一个需求的SRC。
6. **采用不是命中**：真正用于本轮分析的资料才导入本需求source-manifest，保存adopted_sha256、业务last_updated（未知null）、版本和权威声明。相对路径基于显式project-root；资料需在该根内，不用隐式cwd或越界路径。

## 权威与语义判断

当前已发布需求/正式业务规范优先于历史已发布资料；历史草稿、会议记录、AI推断只作线索。现网行为/代码与文档不同，登记冲突让产品确认，不自动选一方。技术资料即使命中也不等于当前可行；技术评估另按feasibility-assessment.md核对实际能力和范围；资料不足保持unknown，能力核实登记ask_dev。

- **冲突**：列出新提议与历史规则的具体互斥预期和各自出处，新增CNF并关联P0问题。新需求默认是变更提议，不是覆盖授权；产品选择沿用、修改、排除或重构后才形成变更建议，历史文件仍只读。
- **重复**：说明实际重合的角色、输入、动作、输出和范围。提出复用已有功能、补充差异、取消重复或按缺陷修复等选项；未获回答不擅自合并或排除。
- **依赖与影响**：按add/modify/remove/replace/refactor说明建议变更类型，分别列直接/间接影响、需调整的历史条目、需重验AC和建议方案。缺少显式关系仍需内容对照找隐含关联；不以图未连通声称无影响。

同需求版本用 `compare_baseline.py --baseline OLD --proposal NEW [--related-analysis PATH ...]`。每份结果先过唯一校验器，旧/新同需求两版本不同时放入跨需求注册表。脚本输出条目差异、完整before/after、有向影响候选和路径、需重验AC，并记录资料清单及非条目节差异。related_ids是泛关联，图候选须语义确认；missing不代表删除授权。跨需求语义重复/冲突由上述分析完成，不用关键词相同自动下结论。

## 保存采用与基线

通过update_analysis补丁设置可选 `context.history_review`：

- `status`: not_performed / reviewed / stale。
- `reason`: 本轮对照范围、未做或待重评原因。
- `source_ids`: 本需求实际采用的SRC，新增可用$别名；每项有adopted_sha256。
- 可选`baseline`: requirement_id、analysis_revision、source_id、publication_basis，表示**本需求**明确采用的当前发布分析版本。对应来源authority=current_published，有发布依据；同时设置meta.baseline_revision。这两项须用户明示actor=user/user_statement，模型不能凭检索自动登记发布版。

不同需求历史规则可用于冲突/依赖，但不冒填成本需求的baseline_revision；没正式基线保持null。source-manifest的revision是资料自身版本，meta.baseline_revision是发布分析修订，二者不是同一计数。

发现内容和取舍写入现有CNF/Q、DEC/ASM、impact_analysis，跨需求引用用REQ/条目ID，并显式传--related-analysis。新字段均为1.0可选扩展，旧结果无需补；只读校验器检查引用、指纹格式及基线声明一致，不证明发布声明真实或语义已经查全。

## 过期与重评

- **年龄提醒**：检索可指定--as-of YYYY-MM-DD、--max-age-days（默认365）。超过阈值提示复核；更新时间未知或未来值也提示，不用mtime补业务时间。不仅因资料老旧就宣布业务规则作废，也不将技术猜测写成事实。
- **内容/依据变化**：每次继续分析或交接前，用 `compare_baseline.py --check-sources ANALYSIS --project-root ROOT` 检查实际采用指纹（跨需求结果显式提供）。索引过时应先刷新，变化正文在刷新前不作为可用命中。
- 检查报告needs_reassessment后，读新版本、保留旧原文版本，按new_source_version新增SRC和受影响集，保存stale/not_ready及history_review.status=stale；关联已关闭问题显式重开、保留answer并说明原因。
- 然后逐项重评实际变化及直接/间接影响，改判AC/规则和问题。完成后另用supplement保存reviewed及实际readiness；不能只把stale字样清掉。新证据confirmed正文仍须actor=user和实际新文档来源，不以推断覆盖。
- 原始资料可能原地变动；在更新采用指纹前，将旧版本保存在独立版本路径，并在旧来源预先登记archived_path保留追溯。只有同一路径的较新版本已经显式采用时，检查器才用归档核验旧版；仅有归档不能掩盖尚未处理的live变化。检查工具不自动改分析状态，分析写入仍只有update_analysis。

## 缺资料与文件归属

无历史资料时记录history_review.status=not_performed、source_ids=[]和原因，baseline_revision=null，报告明确“未做历史对照，不代表无冲突”；仍继续当前需求基本分析，不伪造历史关联。

`index/` 由索引脚本维护，原资料只读；`analysis/` 仍由分析补丁维护，历史基线文件不写。索引共享 `.analysis.lock`，完成后的 `null` 事务允许，未完成事务阻止读取或重建。两索引指纹不一致则拒绝检索，重新索引可恢复。支持[本地工作区](incremental-update.md#本地工作区与锁)中的普通 UTF-8 文本；PDF 或图片须先人工提取文本并保留原文件及位置。
