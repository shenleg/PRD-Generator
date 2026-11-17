# Requirement Analyst 测试与历史证据

本目录收纳需求分析 Skill 的测试代码、辅助模块和重放驱动。命令从仓库根目录执行，详见 [统一测试说明](../README.md)。下文 `fixtures/`、`expected/`、`scenarios/` 分别指 `tests/fixtures/requirement-analyst/`、`tests/expected/requirement-analyst/`、`tests/scenarios/requirement-analyst/`；`results/` 仍指 `tests/results/` 下保留原位置的历史运行记录，不是当前目录的子目录。

当前资料入口：[输入夹具](../fixtures/requirement-analyst/)、[人工参考](../expected/requirement-analyst/)、[场景剧本](../scenarios/requirement-analyst/)。夹具和已认可正文只移动、不改字节，其中旧路径仍是历史来源标识；逐文件当前位置见 `tests/results/repository-layout/test-materials/migration.json`。场景中的现行资料路径已更新，历史运行证据及其哈希不改写。

只运行本 Skill：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests/requirement-analyst -p 'test_*.py' -v
```


阶段1～8已按用户批准的范围完成；整体收口及最新测试结果见`results/final-acceptance.md`和`results/final-acceptance-test-summary.json`。阶段8提交为`be0f8ba`，当时212项回归通过；最终验收另新增4项链路检查。真实下游Skill集成继续延期，八项量化评价指标的统一基线/阈值尚未收口，不扩大为全规格量化达标声明。项目安装和既有真实自动调用见`docs/requirement-analyst/installation.md`、`test_skill_installation.py`。下文保留各阶段历史次数、执行范围与日志；旧模型源码指纹由`historical_sources.py`读取历史提交或快照，不改旧哈希冒充当前行为。当前脚本仍另作完整回归和补丁重放。

本目录区分格式测试、Skill 静态契约检查、已保存的模型行为试跑及确定性交接测试。Python 测试不调用模型或产生额外 API 费用；写入类测试只使用独立临时工作区，保留已保存的历史证据。

## 阶段8知识沉淀

用户选择本会话逐项批准、合成案例及公开CLI集成测试，后续实际选择“批准 DK-001”。`test_domain_knowledge.py`的13项测试在临时项目执行知识写入CLI和既有索引/检索CLI，覆盖批准指纹、事实资格、来源变化、路径、不覆盖及事务门禁；其中合成批准只是测试输入，不是实际入库授权。`test_stage_8_runs.py`另以4项检查核对真实用户批准、准确正文/范围、5步CLI证据及产物指纹。流程和协议见生产`references/domain-knowledge.md`，最终验收见`results/stage-8.md`，启动记录见`results/stage-8-start.md`。本次仅隔离合成项目的受控入库，不声称独立模型盲测或安装自动调用重测。

阶段7历史模型/源码指纹改为读取已提交`6325078`，产物仍保留原字节；旧CLI场景继续用当前工具实际重放，不改旧指纹冒充模型重跑。

## 最终贯穿案例

`run_final_acceptance.py --output NEW_DIRECTORY`以当前公开CLI重放阶段4已有采购模拟案例的五轮补丁，仅将首轮资料路径重定位到新工作区，业务内容、回答和完成清单不变。16次调用覆盖缺分析回交、逐轮保存/校验、报告视图、草稿版本同步、旧修订/旧补丁拒绝及风险草稿。`test_final_acceptance.py`另核对证据指纹并在临时新目录重放；已存在输出目录必须拒绝。重放不是新模型分析、真实用户答疑或真实下游Skill集成。

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/requirement-analyst/run_final_acceptance.py --output /path/to/new-final-acceptance
```

## 自动检查

在仓库根目录执行：

```bash
uv run --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests -p 'test_*.py' -v
```

- `test_schemas.py`、`test_validate_analysis.py`、`test_report_template.py`：阶段 1 格式与校验器回归。
- `test_skill_contract.py`：当前阶段的入口、引用和测试材料检查，不能代替实际模型行为。
- `test_stage_2_runs.py`：读取已保存的真实模型输出，检查正式样例的校验、拆分、状态、提问与结束；另从只读响应日志核对探针的轻量价值分析。所声明执行方式对应的证据缺失必须失败，不静默跳过。

- `test_update_analysis.py`：补丁协议、编号、confirmed 保护、撤销方向、显式更正、新版重开、来源、只读预检、并发及中断恢复，均在临时目录运行。
- `test_gap_validation.py`：阶段 2 配套的缺口封装、唯一接收、显式引用及只读校验；接收写入与故障恢复测试位于 `tests/prd-generator/test_gap_handoff.py`，记录见 `tests/results/prd-generator/stage-2.md`。
- `test_stage_3_support.py`：新版输入只含已审核变化，报告能读取新标准完成清单。
- `test_stage_3_runs.py`：读取阶段 3 真实补丁、逐轮响应和快照；另在临时工作区按原顺序重放全部补丁，核对当前写入器无内容漂移。

## 行为试跑的依据和输入

- 人工已审核的参考要点位于 `expected/`，适用范围与审核记录写在各文件开头。
- 场景剧本位于 `scenarios/RA-xx.md`，包含输入、分轮回答和核对清单。
- 只有 `fixtures/` 中的需求原文或合成探针可以交给被测模型，不能交给它参考答案、黄金结果或预设的后续回答。
- 合成探针只验证提问策略，不代表用户真实系统或产品决定。测试中的模拟 user_answer 不作为正式需求确认。

## 阶段 2 的历史证据

以下阶段 2 记录保留原执行范围，并绑定验收提交 `1d20342`（不依赖克隆时未携带的本地标签），不用于冒充当前补丁机制已回归。

### 当时如何执行模型

本阶段使用当前执行环境中的独立模型会话，显式读取 Skill 源码及其按需引用；调用方只指定测试编号、项目、输出目录和轮次配置。没有新增 API 客户端、API Key 或自动批量收费脚本。

这是显式加载源码的行为试跑，不是安装后斜杠命令或自动触发的集成测试。模型必须保留实际输出，主会话按照已审核要点和确定性的程序断言核对，不接受模型自报“场景 pass”作为证据。

执行环境禁止子模型写 Markdown 报告后，用户已明确批准调整分工：子模型只做业务分析 JSON 和对话，主会话独立使用 `render_trial_reports.py` 校验正式 JSON 并整理报告。该工具仅为测试数据视图，不随 Skill 安装、不补充业务规则。缺少报告的原子试跑仍按 partial 保留，不冒充单一子模型的端到端通过。

模型试跑产物位于 `workspace-sandbox/stage-2/`，由 `run-manifest.json` 的 attempt 选择当前 `attempt-NN/`；旧尝试保留，不用旧文件混成新一次输出。以下目录均相对当前尝试：

- `high-low-voltage/`：第一样例及上限/结束分支。
- `task-management/`：第二样例拆分结果与逐轮澄清；首轮结果保留在 `snapshots/turn-01/`。
- `probes/idea/`：有正式 JSON 的模糊想法探针。其余后端、缺陷与价值探针改为纯只读会话，实际响应记录在 `tests/results/stage-2-text-probes.json`，不要求或宣称已有正式 JSON。
- 各需求的正式结果、报告及清单保存在 `requirements/<编号>/analysis/`；候选 JSON 不作为正式结果读取。
- `turn-NN.json` 保存实际 assistant_message、asked_question_refs、control_questions 及当前输入来源。只登记的问题不等于本轮实际提问。

上一级的 `run-manifest.json` 记录 Skill、校验器及输入的 SHA-256。相关文件变化后，旧产物不能继续证明新版本行为已通过，需要重新试跑，而不是只重写哈希。

本阶段最后一次修改仅新增导出专用检查段落，已对受影响的 REQ-2026-005 实际执行内部重评并保存 turn-04。`scoped_rechecks` 保留精确新增文字、修改前后哈希、适用范围和真实响应/校验路径；测试核对移除该唯一段落即可还原原版。这个记录只证明对应范围已重评，不代表所有非导出输入重新盲跑。超出该精确范围的后续变更仍必须重新运行相关行为场景。

## 阶段 3 的实际补丁运行

当前模型显式读取 Skill 和按需参考，只接收原文及实际发生的逐轮模拟输入，生成补丁；主会话原样接收后调用真实 update_analysis.py。模型不读取参考要点、后续预设回答或旧黄金结果。工具不调用额外模型 API，不是安装后的自动触发验证。

证据位于 `workspace-sandbox/stage-3/`：

- `workspace/`：按正式规格的 projects/<project>/requirements/<id>/ 布局，由更新脚本维护 common、结果、来源和事件；报告另由主会话整理。
- `evidence/<project>/<record>/`：原始 patch、真实脚本 response、来源指纹及当时 analysis 快照。故意失败也保留，不覆盖旧尝试。
- `dialogue/` 与 `turns.json`：实际响应、输入、实际提问引用及控制确认；对话的 Markdown 排版和引号可规范化，业务文字与选项保留。driver 注入记录明确不是模型自然错误或用户回复。
- `unapplied-candidates/`：质量修正前未提交的候选，不当正式结果读取。
- `source-snapshots/`：规则修正前源码；版本清单明确“冲突候选有效状态”定点重评范围，不宣称所有无关输入再次盲跑。
- `run-manifest.json`：最终源码和输入指纹、补丁实际顺序及固定回放时刻。脚本实施期间的写入保护修复用当前脚本完整重放所有真实补丁验证；不重调用模型、不改其补丁或已保存业务快照。

`stage_3_trial_support.py` 只作原样收集和应用一次补丁的测试辅助，不是业务分析引擎，不随 Skill 安装。锁、恢复日志和临时替换文件由 .gitignore 排除；结果、事件、失败及对话证据仍保留。

## 阶段 4 的最小消费者交接验证

- `tools/minimal_prd_consumer.py`：仓库级消费者，不随分析 Skill 安装。复用唯一校验器，只读分析，写简化草稿和 `requirement.json/prd`，不做完整 PRD、发布或模型调用。接口、退出码和恢复边界见 `tools/README.md` 及规格 10.5。
- `test_minimal_prd_consumer.py`：临时工作区验证 RA-24～RA-29、三种就绪度、fail/warning 优先级、文件归属、显式关联资料、并发版本互斥及写入失败现场。
- `run_stage_4_handoff.py`：保存六个合成场景的实际脚本响应、补丁和快照，再复制三个阶段 3 已有结果进行消费。`test_stage_4_runs.py` 独立核对证据、来源指纹及回流事件。
- `workspace-sandbox/stage-4/attempt-02/`：当前通过的证据；根清单选择 attempt=2，attempt-01 保留驱动器输入错误及真实拒绝响应。`run-manifest.json` 区分合成场景和旧样例消费，记录来源及产物 SHA-256；不是新的模型试跑或真实需求验收。

重放至**不存在的新目录**，不覆盖旧证据：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/requirement-analyst/run_stage_4_handoff.py --output /tmp/stage-4-handoff-new-run
```

RA-29 中，消费者只返回缺口请求，场景的分析侧明确审阅并构造合成补丁，由真实更新器登记新问题。它证明接口和持久化链路可行，不证明模型自主回流。需求试用一项已按用户批准以模拟案例代验；下游 Skill 实际集成已另获批准延期，安装及自动调用已实际收口通过，入口不再提供独立斜杠命令。未额外创建用户未要求的阶段完成标签。

## 阶段 4 的模拟业务试用

用户另要求模拟一个贴近实际的需求试用，原文为 `fixtures/stage-4-procurement-withdrawal.md`。独立会话受隔离限制后，用户明确选择改由主会话直接试用，因此这是主会话分析并模拟业务回答，不是独立盲测或真实需求验收。

证据在 `workspace-sandbox/stage-4/simulated-trial-01/`；`stage_4_simulated_trial_support.py` 原样调用真实更新器和消费者 CLI，拒绝覆盖旧证据。`test_stage_4_simulated_trial.py` 有6项保存证据核对，不重新调用模型。`results/stage-4-simulated-trial.md` 记录分轮、执行方式调整、当前方案和保留缺口。原始阶段4的127项记录保留，本次完整133项回归另存 `results/stage-4-simulated-trial-test-run.txt`。

最终5次补丁保存均pass；业务汇总分类Q-12仍open P0，停止后保持completed/not_ready，消费者实际输出warning风险初稿。模拟试用链路完成不等于业务就绪。2026-11-16用户明确批准以该模拟案例满足本次阶段4需求试用退出条件；来源和业务就绪度不变，实际下游集成已批准延期，自动调用后续已实测通过。当前验收状态见 `results/stage-4-acceptance.md`；旧试跑清单与日志保留当时状态，不重写原证据。

## 阶段5完整验证

在阶段4提交 `3ddb876` 后建立独立分支。用户批准合成历史资料及CLI测试边界，不将夹具或draft冒充真实已发布基线。首个增量历史记录保留在 `results/stage-5-start.md`；当前完整验收见 `results/stage-5.md`。

- `test_compare_baseline.py`：真实CLI比较同需求条目/非条目节及来源变化、有向影响与AC重验、输入只读、撤销/待重评、无资料降级、校验fail优先及坏JSON/身份/参数边界。
- `test_history_contract.py`：显式发布依据和采用来源别名、基线登记权限、历史指纹变化、旧版本归档不掩盖新变化，全部经更新器/对照CLI验证。
- `test_project_sources.py`：显式索引、有限检索及筛选、证据位置、源变化排除、索引世代不一致、过期/未知/未来时间、越界与符号链接、完成null/未完成事务。
- `test_stage_5_runs.py`：独立核对六场景保存的真实结果、CNF/Q、取舍选项、影响路径、两阶段重评、旧问题重开/答案保留、不可变基线及独立空项目，并将19次CLI链路重放到临时目录。
- 当前证据由 `workspace-sandbox/stage-5/run-manifest.json` 选择attempt-04；attempt-01/02/03保留各自验证范围，不混称全量盲跑。`semantic-execution.json`记录独立只读分析被阻止落盘后，用户授权主会话完成补丁保存的分工。
- `installed-skill-verification-02.json`是最终代码实际CLI自然语言自动触发当前Skill、加载historical-retrieval并识别冲突的最小脱敏提取（首次提取单独保留）；没有原始会话、实际session编号、初始化元数据或本机路径。独立实际调用不等于全部合成补丁由模型端到端生成。

全部Python测试不调用模型；历史模型来源仍绑定旧版本，当前语义烟测另有当前源码指纹。重放时指定**不存在的新目录**：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/requirement-analyst/run_stage_5_trial.py --output /tmp/new-stage5-trial
```

## 阶段6技术可行性

用户批准使用合成技术资料，未提供真实系统架构确认。`fixtures/stage-6/`含限定查询、可扩展作业、压测风险、部署禁令、缺资料、旧草稿、局部接口及权限未定共8个case。

- `workspace-sandbox/stage-6/`保留3次真实只读CLI模型执行的最小脱敏输出。主体调用覆盖8例；首次错行号不作最终引用，第二次修正证据位置；TECH-PARTIAL核心业务问题误列P1后仅对该例实际重评。`selected-model-evidence.json`按case_origins选择7+1实际输出，旧原文和规则快照保留，不改模型结论或问题优先级，不声称全部重新盲跑。
- `run_stage_6_trial.py`只重放保存评估，不调用模型：技术结论/证据正文/影响/问题原样映射为补丁别名，经实际更新器、校验器和消费者CLI落盘。业务骨架、完成清单和readiness由主会话合成驱动器提供，不代表完整业务需求分析。
- `test_feasibility_cli.py`验证五种结论现有1.0字段、非unknown缺证据及产品问题误作技术引用被唯一规则9拒绝且旧文件不变。
- `test_stage_6_runs.py`的8项独立核对涵盖实际来源、可核对定位、五种语义判断、unknown降级、产品P0、输出保真、草稿及24次CLI重放。报告及消费者另有真实遗漏的红绿回归。
- 阶段5的旧行为/源码证据绑定已提交cbb2938；当前工具仍另用原有场景重放，不改旧哈希伪装新行为。

最终验收见 `results/stage-6.md`。重放到**不存在的新目录**，不会重新调用模型：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/requirement-analyst/run_stage_6_trial.py --output /tmp/new-stage6-trial \
  --model-evidence workspace-sandbox/stage-6/selected-model-evidence.json
```

## 阶段7体验与视觉

用户批准合成低保真页面资料，另明确授权浏览器沙箱失败后仅本次本地静态页截图。`fixtures/stage-7/`的PNG由HTML实际渲染，主会话实际看图；HTML仅截图生成用途，分析模型未读取它，模型Read图像载荷实际返回有记录。浏览器未使用既有账号，临时本地服务已停止。

- `model-attempt-01/verification.json`：当前安装Skill实际只读评估六case，按需读取体验参考和图像；缺资料/纯后端无观察事实，有图只作限定呈现事实。没有原始会话、session编号、初始化元数据或图像base64。
- `run_stage_7_trial.py`机械保留四个ux字段、观察、页面候选及问题原文；来源别名/现有条目标签转换后真实更新器保存、校验、报告和草稿交接。业务骨架/清单/readiness为驱动器提供，不声称完整业务自主分析。
- `test_stage_7_runs.py`有9项实际图像/边界/来源/主张核查及18次CLI临时重放；消费者/报告另有遗漏红绿回归。旧阶段6源码证据绑定6fcf4bb，当前功能仍重放旧场景，不修改历史哈希。

当前验收入口 `results/stage-7.md` 与 `workspace-sandbox/stage-7/run-manifest.json`。重放到不存在的新目录，不调用模型或浏览器：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/requirement-analyst/run_stage_7_trial.py --output /tmp/new-stage7-trial \
  --model-evidence workspace-sandbox/stage-7/model-attempt-01/verification.json
```

## 分轮与计分

先保存并核对首轮，才按实际问到的语义提供剧本回答；用户的结束要求单独作为后续输入。未发生的回答不能提前混入结果。第一样例的上限控制确认和业务问题分别说明，但所有发生提问的轮次均计入记录。

场景共用一次实际运行时，记录各自检查的不同性质，不虚构为多次独立试跑。结果及无效问题的具体判定保存在 `results/stage-2.md`；没有实际证据的项保持未完成，不因为文件存在就记 pass。
