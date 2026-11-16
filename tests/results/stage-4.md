# 阶段 4：最小消费者及交接场景验证

## 当前验收说明

本文保留消费者子阶段完成时的记录。后续模拟试用已完成，且2026-11-16用户明确批准以该模拟案例满足本次需求试用条件；当前只剩实际下游集成及安装自动调用等收口验证，详见 `stage-4-acceptance.md`。不再将补交真实项目材料列为本次试用验收前置，以下历史测试次数及原试跑证据不改写。

## 本次结论（子阶段完成当时）

**已完成用户指定的本次子范围：最小消费者脚本及 RA-24～RA-29 确定性交接验证。** 完整回归 127 项通过，0 失败、0 错误、0 跳过。

**阶段 4 整体验收尚未完成。** 真实需求稍后由用户提供；下游真实 Skill 集成、最终调用配置收口及安装后自动调用仍待验证。本次不打完成标签，不自动提交、合并或推送。

## 主要产物

- `tools/minimal_prd_consumer.py`、`tools/README.md`：复用唯一校验器，严格读取分析及来源；按状态生成简化 Markdown 草稿或返回交接请求；只维护自己的草稿和 requirement.json/prd，不写分析。
- 规格 10.5：明确本地草稿序号、三种就绪度门禁、状态过滤与追溯、缺口回流接口、修订检查、共享锁及保存失败边界。没有新增分析结果字段，schema_version 保持 1.0。
- `tests/test_minimal_prd_consumer.py`：20 项门禁、文件归属、状态与来源、回流、并发和失败测试。
- `tests/run_stage_4_handoff.py`、`tests/test_stage_4_runs.py`：实际运行证据收集及 7 项独立核对/重放测试。
- `tests/scenarios/RA-24.md`～`RA-29.md`：输入、模拟回答、核对项和依据。
- `workspace-sandbox/stage-4/`：保留第一次驱动错误及第二次完整通过的证据，由根清单选择 attempt=2。

分析 Skill、更新器、校验器、Schema 均未修改；阶段 3 源码指纹检查及原 100 项回归保持通过，没有重写历史证据哈希来冒充模型重跑。

## 场景结果

| 场景 | 实际验证 | 结论 |
| --- | --- | --- |
| RA-24 | 缺结果返回 analyze，不创建需求或草稿；返回请求不等于已启动分析 Skill。 | pass |
| RA-25 | 默认要求重评；模拟明确坚持后只生成标“基于过期分析”的 warning 草稿。另有 fail 优先于 stale 的回归。 | pass |
| RA-26 | completed/not_ready 仍只生成含风险、open P0 的初步草稿；三个旧样例补充覆盖三种就绪度。 | pass |
| RA-27 | revision=1 草稿后真实补丁推进到 2；比较得 pending，不另存待同步字段；重生成后 current，旧草稿保留。 | pass |
| RA-28 | inferred、assumption、待验证信息、to_reassess 和逐条映射保留；withdrawn 内容不摘录。 | pass |
| RA-29 | 模板要求验收但无条目时返回缺口请求；分析侧实际补丁登记 Q-1/P0/open，清单第 7 项未满足、not_ready；旧草稿待同步。旧补丁重放被拒。 | pass |

当前证据包含 **14 次消费者调用**（5 pass、9 warning）、**8 次分析更新器调用**（6 pass、1 warning、1 预期 fail）和 **9 份实际生成草稿**。快照另留三份草稿副本，不重复计生成次数。

其中消费者 warning 是无结果、过期、未就绪、条件就绪或缺口回交等预期状态，不是假称全部结果均可正式交付。分析更新的 fail 是 RA-29 故意重交旧修订补丁，未新增重复问题。

## 真实运行与合成输入的区别

六个交接场景用明确标注的合成补丁验证脚本；没有调用模型。RA-29 的分析侧补丁由场景明确审阅后构造，优先级与完成清单是该场景的分析侧选择，不是消费者通用算法，也不证明模型已经自主分析并登记缺口。

另复制三个阶段 3 已保存的正式结果，在独立工作区实际运行消费者：

| 已有结果 | 就绪度 | 消费者结果 |
| --- | --- | --- |
| PROBE-BACKEND | ready_for_document | pass，待确认草稿 |
| PROBE-NOTIFICATION | conditionally_ready | warning，保留遗留事项 |
| REQ-2026-001（第一业务样例） | not_ready | warning，风险初稿 |

原件不变，复制后的 analysis JSON、来源、事件和报告逐字节不变；这只是对旧模型结果的消费，不是新一轮模型分析或真实需求试用。

## 发现的问题及修正

1. 最先运行新增测试时消费者文件不存在，得到 FileNotFoundError，确认测试能够因缺实现而失败。
2. 初版合成假设误把 verification 写为对象，且两个问题漏了 related_ids；唯一校验器明确拒绝。按现有 Schema 修正测试输入为字符串验证信息、补齐引用，不修改 Schema 迁就测试。
3. 第一次证据保存的过期合成初始状态误用 stale/ready_for_document，更新器拒绝：warning 只允许保存 stale/not_ready。保留 attempt-01 的补丁与真实 fail；只修正驱动输入，在全新 attempt-02 重跑通过。
4. 保存逻辑明确区分草稿落盘和元数据替换：注入元数据替换失败时旧指针不变，新草稿保留、下次拒绝覆盖；元数据已替换后若目录同步失败，仍报告 fail，同时如实返回 written=true，不把部分保存当成功交付。

## 文件归属与恢复范围

消费者沿用工作区独占锁，在同一锁内读取、校验、比较和写草稿。发现待恢复分析事务就拒绝消费，交由分析更新器恢复；没有复制分析事务恢复逻辑。可显式携带 expected_revision，冲突须重新读取。

草稿先不覆盖地写入，再原子替换 requirement.json；保留 common、其他块及 prd 扩展字段。最小工具不承诺完整 PRD 事务恢复，失败或中断留下的未提交草稿、临时文件保留供人工检查，不自动删除。`.prd-write-*` 加入忽略，业务草稿及证据不忽略。

## 下游试读与剩余工作

独立静态试读记录见 `stage-4-downstream-read.md`：测试点分析、用例设计能从验收/边界/异常及引用中提取可用内容；没有发现必须新增的 Schema 字段。自然语言验收、未答问题及未知协议仍需真实消费者确认。**静态试读不等于真实下游 Skill 集成通过。**

阶段 4 剩余：

- 用户提供 2～3 个真实需求，至少包含一份不规范真实文档；至少一个走完“分析到简化草稿”。
- 实际下游测试 Skill 读取并使用结果，记录缺字段或歧义；有具体问题再兼容扩展协议。
- 到配置收口步骤设置 user-invocable:false，并实际验证安装后的自动调用。本次只完成消费者子范围，调试配置保留，不声称自动调用已通过。

不进入阶段 5，不写 compare_baseline.py，不开发完整 PRD Generator。

## 如何复核

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests -p 'test_*.py' -v
```

重放当前脚本至不存在的新目录，保留已有证据：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/run_stage_4_handoff.py --output /tmp/stage-4-handoff-new-run
```

日志：`stage-4-test-run.txt`；测试汇总：`stage-4-test-summary.json`；交接汇总：`stage-4-validation.json`。证据清单记录当前源码及 114 份产物指纹，独立测试同时核对具体响应、草稿、问题和事件，不以清单自报成功代替验收。
