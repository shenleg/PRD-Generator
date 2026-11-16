# 阶段 4：下游字段静态试读

性质：独立只读检查，从测试点分析、用例设计两个消费者视角读取现有 JSON。没有运行真实下游测试 Skill，不计作实际集成验收通过。

## 输入

- `workspace-sandbox/stage-3/workspace/projects/probes/requirements/PROBE-BACKEND/analysis/analysis-result.json`
- `workspace-sandbox/stage-3/workspace/projects/task-management/requirements/REQ-2026-005/analysis/analysis-result.json`
- 规格第十节。其直接约束 PRD Generator，测试消费者可借鉴只读、标签、状态与追溯原则，但不声称已有完整的测试 Skill 交接协议。

## 可直接读取的内容

| 视角 | 具体试读 |
| --- | --- |
| 测试点分析 | PROBE-BACKEND 的 AC-1/2/3 可拆出有权成功、任务不存在、无权访问；BND-1 补空 task_id 边界，EXC-1 提供异常线索。 |
| 用例设计 | PROBE 的 AC-1 → FR-1：预置存在且有权任务，传非空 task_id，检查对应 result_id/status；AC-2 → BR-1 检查 not_found；AC-3 → BR-2 检查 forbidden。 |
| 边界与阻塞 | 导出 BND-3 可识别 5000 上下的边界；BND-1/2 指出生命周期、权限，EXC-1/2 指出部分输出和行集时点。Q-15、Q-13/14 等仍未回答，不能据此确定超限动作、日志覆盖或日志失败政策。 |
| 追溯 | related_ids 连接规则、边界和问题；sources 中的 SRC 与 location 提供依据。tag 区分确定性，status 区分生命周期，二者不能互相替代。 |

## 不能据此补出的内容

- 后端空输入的协议结果、真实接口路径、字段格式、HTTP 状态码仍需研发确认，不能从 not_found/forbidden 文本猜出协议细节。
- 导出 5001 条可列成待澄清的边界用例，不能把推荐当作拒绝、截断或分批策略的正式预期。
- 导出 AC-1 是 inferred 的汇总草案，`not_ready` 且完成清单第 7 项未满足，不能把 active 自动解释为可完整验收。
- 旧 BR-1/2/3、ASM-1 为 withdrawn，旧 Q-1 为 dropped；当前问题为 Q-15 等，历史条目不得当现行规则。
- 自由文本来源定位及自然语言验收可供试读和追溯，但不等于稳定的机器锚点或可执行断言。

## Schema 判断

本次未发现必须新增的字段。现有 acceptance_criteria、boundaries、exceptions、content、related_ids、tag、status、sources、questions、meta 足以提取测试点、识别阻塞并追溯，因此保持 schema_version=1.0。

这不等于已证明自动用例生成充分。后续真实测试消费者若确需原子条件/预期或类型化关系，应先提出具体失败样例，再按兼容规则扩展，不在本次预设结构。
