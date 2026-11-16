# 阶段6验收：有依据的技术可行性

## 结论

**阶段6已按用户批准的合成技术资料范围完成，RA-20、RA-21验证通过。** 完整回归 **184项通过，0失败、0错误、0跳过**。

当前Skill能按有效资料限定判断supported/conditionally_feasible/risky/unknown/conflicting；资料缺失、旧草稿或只证明局部能力时保持unknown，产品范围未定仍留产品P0。报告和实际消费者均保留技术证据、影响、前提和风险。

这不是现实系统架构核验或上线批准：资料、技术负责人和业务背景均明确为合成。技术判断由实际已安装Skill的独立只读CLI生成；主会话驱动器机械映射技术内容，业务骨架、完成清单及readiness由驱动器提供，不冒称完整业务需求端到端自主分析。

分支：`feat/stage-6-feasibility`，HEAD仍为阶段5提交`cbb2938`。阶段6未提交、未合并、未推送、未打标签，未进入阶段7。阶段4延期的真实下游Skill集成仍延期，不因本次验证通过而改成已通过。

## 实现范围

- 新增`references/feasibility-assessment.md`：证据有效性、五种判断、局部/整体能力、产品与研发责任、就绪度独立、资料变化后重评。
- Skill入口新增按需技术参考、更新硬规则与当前边界，保持54行，不fork、不开放独立斜杠入口。
- 清理analysis-framework/historical-retrieval里已过时的“本阶段不做技术评估”说明。
- 报告渲染按实际technical_feasibility展示，不在有结论时仍说“未开展”。消费者补保留非条目技术节，避免丢前提、证据和风险。
- **沿用原Schema、更新器和规则9**。规则9原已启用，本阶段没有第二个校验器、技术打分脚本或新的Schema版本；schema_version仍为1.0，省略技术节的旧结果仍合法。
- 阶段5旧证据的源码指纹绑定已提交cbb2938；新能力另有实际模型输出，旧哈希、模型回答和原产物不重写。当前工具仍用旧场景全量重放。

## 实际评估与验收表

| 合成case | 资料及关键事实 | 最终实际模型结论 | 验收 |
| --- | --- | --- | --- |
| TECH-READ | 当前接口已核实按非空task_id返回result_id/status，现有身份与项目权限、not_found/forbidden不变 | supported，仅限既有契约 | RA20 pass |
| TECH-CSV | 数据字段和作业扩展点明确，但CSV适配器、触发/下载接口及回归未实现 | conditionally_feasible，保留改造前提 | RA20 pass |
| TECH-LOAD | 全量加载内存原型在100并发已有回收暂停信号，新目标1000并发未验证 | risky，不承诺必达或必失败 | RA20 pass |
| TECH-NETWORK | 本期必须直传公网，同时规范禁公网且不可加代理/改出口 | conflicting，产品/安全取舍仍open | RA20 pass |
| TECH-NO-DOC | 没有技术资料，不借其他case资料补能力 | unknown，evidence空，登记ask_dev | RA21 pass |
| TECH-OLD | 唯一证据为2020旧草稿且现行性未确认 | unknown，旧设想不当当前接口证明 | RA21 pass |
| TECH-PARTIAL | 只证明标识查询，明细/分页核心能力不明；全部结果范围/时点也未定 | unknown，核心产品问题P0/not_ready | RA21 pass |
| TECH-PRODUCT | 管理员可看哪些项目没有产品决定，技术能否改跨项目也未核验 | unknown，产品权限P0与研发能力问题分开 | RA20/21 pass |

上表结论与模型实际结构化输出一致，测试从合成文档明确契约、改造点、风险信号及硬约束独立判分，不以模型自报pass替代核对。未知不是结构错误；supported也不是代码实现、容量实测或发布批准。

## 实际执行及证据选择

1. **模型尝试1**：真实已安装Skill按自然语言任务读取8个合成case及明确技术资料，结论方向正确，但部分数字行号不准确。保留原输出，不作为最终引用。
2. **模型尝试2**：补充稳定章节/条款定位要求，重新实际评估8例。证据位置可核对，技术判断正确；主会话核对后发现TECH-PARTIAL将“全部结果”的生命周期/时点与完整输出问题列为P1，按既有核心完成规则应是P0。
3. **定点尝试3**：保留修正规则前的参考快照，明确核心输出边界P0规则，只实际重评TECH-PARTIAL，不给模型测试期望或旧输出。新结果仍unknown，核心输出/权限均P0；另有非核心输出格式问题P1。其余7例未宣称重新盲跑。
4. **选择与落盘**：selected-model-evidence.json仅按case_origins选用第二次7例+定点1例，每行与原始提取严格相等。未由主会话改写任何结论、证据正文、问题或其优先级。
5. **实际脚本**：最终attempt-02执行8次update_analysis、8次validate_analysis、8次消费者，共24次CLI：20pass、4warning。8份结果、报告、草稿实际存在；warning为产品P0导致的风险草稿。消费前后分析JSON、来源、事件和报告指纹一致。

三次模型调用保存的都是本任务必要脱敏工具调用和结构化评估提取，不保存原始会话、实际session编号、初始化元数据或本机绝对路径。主体8例共享一次只读模型调用，并非8次隔离盲测；每例采用证据必须在该例materials中，测试明确核对。

业务条目、完成清单和就绪度是合成驱动器为保存/交接测试提供的骨架，不是模型自主完成的完整需求分析。未回答产品问题仍open，特别是性能方案取舍、部署冲突、全部结果边界和跨项目权限。没有真实业务取舍被本次测试替用户确认。

## 发现的问题及修复证据

- 报告对已经存在的技术结论仍写“本阶段不开展技术评估”，新增测试先失败，再改为按保存结果展示；无技术节则明确未评估，unknown则明确资料不足。
- 最小消费者只摘录条目和问题，遗漏technical_feasibility整节；新增测试实际失败后，原样保留结论、证据、可信程度、影响、风险及研发引用。
- 首次模型引用数字行号有误，要求优先用真实章节/条款或原文段落后实际重跑；测试不接受错误行号，也不通过主会话静默修正文案掩盖模型错误。
- 核心全部结果问题被降为P1，通过明确通用优先级规则并定点实际重评修正，保留旧模型输出、旧保存尝试及参考快照。
- 规则9的公开CLI负例：四种非unknown空证据均拒绝，旧修订/结果/事件原字节不变；technical.related_questions误指产品问题也被同一规则9拒绝，不能用合法Q编号凑通过。

没有修改校验器去迁就模型。代码保持规则9只检查结构和引用，证据语义由当前分析和独立原文核对负责。

## 正式产物与复核

生产参考：`skill/requirement-analyst/references/feasibility-assessment.md`。

实际证据入口：`workspace-sandbox/stage-6/run-manifest.json`。

- `model-attempt-01/02/03-scoped/verification.json`：三次实际只读模型输出的最小脱敏提取，各自来源指纹。
- `selected-model-evidence.json`：严格7+1选择、各case来源及单点规则演进，不冒充全量再跑。
- `source-snapshots/`：核心优先级修正前实际使用的参考。
- `attempt-01/`：保留带旧P1的第一次保存/消费链路，不作最终就绪度依据。
- `attempt-02/`：最终8份结果、来源、事件、报告、草稿及24次CLI进程状态；181份产物有指纹。

测试新增13项：3项技术CLI、8项已保存模型/脚本证据及重放、1项报告回归、1项消费者回归。此前171项全部继续通过，最终184项。

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests -p 'test_*.py' -v
```

重放到**不存在的新目录**，不重新调用模型：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/run_stage_6_trial.py --output /tmp/new-stage6-trial \
  --model-evidence workspace-sandbox/stage-6/selected-model-evidence.json
```

日志：stage-6-test-run.txt；测试汇总：stage-6-test-summary.json；逐场景范围与限制：stage-6-validation.json。

## 支持范围

本阶段没有真实研发确认、实施方案、成本/工期估算、压测达标承诺、部署或安全策略修改。有效资料只能支持其明确覆盖的范围，不能从有一个接口扩展为所有能力已具备，也不能从过期草稿推断系统当前存在或不存在某能力。

技术结论和文档就绪度独立：合成骨架中仅有研发P1时可为文档就绪，但仍不代表技术实现已确认；有产品核心P0的场景必须not_ready。真实使用需由分析侧完整核对业务完成清单，不能照搬本驱动器的骨架或元状态。
