# 阶段5验收：项目资料与历史需求

## 结论

**阶段5已按用户批准的合成历史资料范围完成实现与验证。** RA-14～RA-19各有真实脚本证据，当前Skill实际能自动加载历史参考完成只读语义对照；完整回归 **171项通过，0失败、0错误、0跳过**。

历史资料的“当前发布”来自明确标注的合成场景声明，不是真实组织发布。用户批准主会话完成语义场景落盘，因此不冒称独立模型盲测端到端通过。阶段4延期的真实下游集成仍是延期项，不阻塞本次范围。

分支：`feat/stage-5-history-baseline`。阶段5未提交、未合并、未推送、未打标签；HEAD仍为阶段4提交`3ddb876`。本次没有自动进入阶段6。

## 分步完成情况

| 增量 | 已实现 | 实际核对 |
| --- | --- | --- |
| 显式版本差异与影响 | compare_baseline对照同需求条目、来源和非条目节，输出before/after、有向影响路径及AC重验 | 8项CLI测试；不沿共享祖先误伤兄弟功能、循环可终止，两个输入原字节不变 |
| 历史语义对照 | 独立只读会话识别互斥删除规则及重复筛选；主会话按授权登记CNF/Q、取舍和变更建议 | RA14/15真实更新器保存，问题保持open，不自动变更/合并历史 |
| 采用与基线保护 | history_review、来源指纹/权威/发布依据/归档、显式基线关联 | 5项CLI契约测试；只有用户明示才登记、改换或解除基线，旧格式兼容 |
| 项目索引与有限检索 | index_sources、search_project及内部共享project_sources模块 | 11项CLI测试；显式catalog、双索引指纹、路径和读取预算、检索筛选、老旧/未知时间、正常null及待恢复事务 |
| 变化重评与无资料降级 | 已采用指纹变化检测、旧索引正文排除、stale保存及真实重评 | RA17两阶段更新BR/AC、旧已答Q重开保留answer；RA18年龄复核；RA19独立空项目与报告 |
| Skill接入与兼容 | historical-retrieval渐进引用、53行入口、新旧Schema及报告视图 | 当前安装入口真实CLI自动调用并读历史参考；旧模型补丁全量重放仍通过 |

`history_review`和来源字段为schema_version=1.0的可选兼容扩展，未迁移旧结果或更改旧业务事实。现有元分析修订号仍只由更新器维护；baseline_revision是用户明确采用的发布分析版本，不是新计数器。

## 六个验收场景

| 场景 | 输入和关键结果 | 结论 |
| --- | --- | --- |
| RA-14 新旧冲突 | 新提议允许删有未完成任务用户，历史要求拒绝且数据不变；CNF关联open P0，not_ready，历史基线快照不变 | pass |
| RA-15 重复识别 | 状态、创建时间区间及组合筛选已有；记录重合出处，提供复用/补差异/缺陷选项，未擅自合并或排除 | pass |
| RA-16 变更影响 | FR-1变化直接影响BR-1，间接影响AC-1和Q-1，附路径与重验清单；旧发布分析只读 | pass |
| RA-17 依据变化 | 资料第二版加冻结保护；检测指纹、刷新索引、新SRC、stale/not_ready、旧Q重开保留答案；随后实际更新BR与AC并恢复reviewed | pass |
| RA-18 老旧资料 | 合成旧架构草稿业务更新时间2020-01-01，as-of 2026-11-16、阈值365天，warning要求复核，不确认当前技术能力 | pass |
| RA-19 无资料 | 单独空工作区没有历史/索引；检索warning、对照degraded、history_review=not_performed，报告明确未做对照，不宣称无冲突 | pass |

当前attempt-04共 **19次真实CLI调用：13 pass、6 warning**。warning为资料老旧、资料变化、旧索引排除、stale保存及无资料降级等预期行为，不是假称所有资料均现行可靠。四份正式分析均通过唯一校验器并有报告。

## 四份正式结果

- HIST-USER-001：当前工作分析revision4，completed/ready_for_document；仍基于明确采用的发布分析修订1，旧发布快照原字节保留。
- NEW-DELETE-001：revision1，clarifying/not_ready；产品是否放宽删除规则及任务归属未答。
- NEW-FILTER-001：revision1，clarifying/not_ready；复用还是补差异的取舍未答。
- NEW-NO-HISTORY：revision1，clarifying/not_ready；基本功能想法缺少核心信息，历史对照明确未做。

“历史冲突/重复已识别并如实登记”是本Skill能力验收，不等于场景中的业务产品决策已经完成；不为凑ready关闭问题。

## 语义与执行证据的边界

独立会话实际读取当前生产Skill及指定四份合成文档，识别冲突/重复并给出真实问法，但候选文件写入被隔离权限保护拒绝。会话停止，没有运行更新器；主会话没有擅自代写绕过，而是提供选择。用户明确选择“主会话完成落盘 (Recommended)”后，才按合成输入编写补丁并通过真实CLI保存。

因此：

- 独立语义只读结果保存在`semantic-execution.json`，不声称其已生成并保存正式分析。
- `run_stage_5_trial.py`中的主会话语义补丁是场景输入，驱动器不是通用语义引擎；Python重放不重新调用模型。
- 当前安装Skill另有实际自然语言CLI烟测，真实调用Skill并读取historical-retrieval，指出新提议未批准、旧基线不能自动覆盖；只保存必要脱敏工具/答案提取，不保存原始会话、session编号、初始化元数据或本机路径。
- 两个实际安装烟测各自保留源码指纹；最终使用`installed-skill-verification-02.json`，首次提取不改写。后续只是索引catalog边界修复，也重新跑了当前代码的烟测和六场景，未用旧产物冒充新版本。

## 发现并解决的问题

1. 影响测试先因无impact输出失败；按被关联者→引用者的有向候选传播实现，保留路径，避免共享目标造成兄弟功能误伤。
2. 仅看条目会遗漏来源修订和非条目节变化；新增测试先失败，再加入来源差异、采用者影响种子及非条目变化列表。
3. 新history_review及基线登记首次不被补丁协议接收；增补兼容字段和唯一校验器关系检查，不另写第二套校验。
4. 基线只写数值、不给发布依据最初可绕过旧格式兼容分支；测试复现后，新增补丁明确要求实际基线采用声明；旧结果不迁移。
5. 索引器最初把正常完成后的null事务日志当待恢复，导致已使用工作区不能索引；实际复现后修复，只拦非空事务。
6. 显式catalog与索引输出同路径时会覆盖输入；独立只读复核发现，测试先复现，再禁止输出路径作为catalog。索引原资料同样不能是受管输出/锁。
7. 复核提出“旧格式基线能被analyst清空”，实测未复现：协议层早有用户明示保护。新增回归确认拒绝并保留原字节，没有为错误判断扩大修改。
8. 资料原地升级需同时保留旧版追溯；检查器仅在较新同路径版本已经显式采用时允许按archived_path核验旧版，避免仅建归档就掩盖live变化。

attempt-01/02/03分别保留最初链路、增加旧问题重开与独立空项目、规范来源类型及报告的验证范围；最终边界修复后用全新attempt-04重跑。旧响应、补丁、报告和指纹未改写。

## 文件与复核入口

生产：

- `skill/requirement-analyst/scripts/compare_baseline.py`
- `skill/requirement-analyst/scripts/index_sources.py`
- `skill/requirement-analyst/scripts/search_project.py`
- `skill/requirement-analyst/scripts/project_sources.py`（脚本内部共享工具，不是第四个用户接口）
- `skill/requirement-analyst/references/historical-retrieval.md`
- Schema、唯一校验器及更新器的兼容历史字段扩展。

证据：`workspace-sandbox/stage-5/run-manifest.json`选择最终尝试；其`attempt-04/evidence/`含真实命令、退出码、stdout、响应及保存快照；`patches/`为主会话授权补丁，`workspace/`及`empty-workspace/`为实际工作区。最终场景121份产物有指纹，发布基线单独核对原字节。

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests -p 'test_*.py' -v
```

重放到**不存在的新目录**：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/run_stage_5_trial.py --output /tmp/new-stage5-trial
```

最终汇总：`stage-5-test-summary.json`；逐场景结果：`stage-5-validation.json`；日志：`stage-5-final-test-run.txt`。初步169项日志也保留，最终171项另存，不覆盖旧运行。

额外独立核验四份结果时，首次误用未装jsonschema的系统python，报ModuleNotFoundError；改用上述既有uv依赖环境重跑，四份结果、全部源码/产物指纹及Python语法均通过。没有为此修改系统Python、依赖声明或配置。

## 支持范围及未做项

- 文本关键词/元数据检索，不是向量语义搜索；显式图不是隐含依赖的完备证明，相关性和冲突仍须分析侧判断。
- Linux/Unix可信本地遵锁工作区；不保证网络文件系统、恶意并发换中间目录或不遵锁外部修改时的快照安全。
- 普通UTF-8文本；PDF、图片、Figma和压缩包没有自动解析器，需保留原来源后人工提取。
- 未做技术可行性结论、完整视觉设计、知识库自动沉淀、正式PRD发布或真实下游测试Skill集成。
- 用户此次没有需要真实产品决策的取舍：场景业务选择均明确为合成；真实使用遇到冲突时仍须用户确认，不能将本次建议当永久规则。
