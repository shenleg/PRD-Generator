# PRD Generator 测试

本目录收纳生成侧格式、缺口接收、门禁、编号、首稿保存、增量同步及公开 CLI 留证测试。程序结果、模型行为和人工认可分别记录；阶段 3～5 已获最终人工认可，阶段 5 的原模型问题、修复及当前源码重放分别留证，阶段 6 增加评审、发布、不可变基线和废弃的合成程序用例，实际范围见[阶段 6 记录](../results/prd-generator/stage-6.md)。

## 维护代码

| 文件 | 用途 |
| --- | --- |
| `test_prd_schemas.py` | 三份 Schema 的结构、兼容与严格补丁边界 |
| `test_prd_validation.py` | 十二条规则、正文定位、引用、缺口、快照及只读边界 |
| `test_prd_format_runs.py` | 保存证据的来源和产物指纹、实际响应及新目录重放 |
| `prd_fixture_support.py` | 构造注明合成的独立临时夹具 |
| `run_prd_format_checks.py` | 在新目录运行十五次真实只读校验并保留证据 |
| `test_gap_handoff.py` | 接收引用、幂等、保存顺序、故障恢复和文件归属 |
| `run_gap_handoff.py` | 真实公开 CLI 与独立故障注入子进程留证，不调用模型 |
| `test_prd_gate.py` | 唯一上游校验、四种草稿门禁、可选资料降级和只读边界 |
| `test_prd_numbering.py` | 正式编号、映射身份、来源摘要、高水位及并发拒绝 |
| `test_prd_draft.py` | 信息视图、统一首稿、重复稳定性、候选保留及故障恢复 |
| `run_prd_generation.py`、`test_prd_generation_runs.py` | 合成场景的真实公开 CLI 留证与新目录重放，不冒充模型输出 |
| `run_model_draft_replay.py` | 用当前冻结源码重放已保存的真实模型候选，不称为新模型调用 |
| `test_prd_sync_check.py` | 只读修订与完整来源比较、五类变化、只改标签/来源/关联和JSON稳定性 |
| `test_prd_sync_write.py`、`prd_sync_support.py` | 最小化同步、编号、缺口关闭/保留、暂定依据、并发与恢复 |
| `run_prd_sync.py`、`test_prd_sync_runs.py` | 在新目录运行阶段4七项场景及分支的公开CLI并核对证据，不冒充实际模型 |
| `test_prd_sync_regressions.py` | 非编号整章保护、稳定章节归属、旧键碰撞、多来源及真实跨进程交接竞争 |
| `prepare_prd_sync_model.py` | 冻结隔离模型输入与Skill快照，不把程序候选或参考答案喂给模型 |
| `grade_prd_sync_model.py`、`build_prd_sync_review.py` | 从真实文件评分客观断言，并使用Skill Creator官方工具生成静态评审页 |
| `run_model_sync_replay.py` | 用当前冻结源码重放实际模型成功候选，单独记录旧稿章节证据不足，不称新模型调用 |
| `test_prd_edit_validation.py` | 兼容正文基准、不一致目标及遗留配对、只读及发布阻断诊断 |
| `test_prd_edits.py` | 排版、手改检测/保留、身份及摘要、旧稿证据、并发恢复与空集合提示回归 |
| `run_prd_edits.py`、`test_prd_edit_runs.py` | 十个编辑分支的公开CLI留证，不覆盖旧目录 |
| `prepare_prd_edit_model.py` | 冻结阶段5四份模型运行输入与源码，不泄露参考或后续回答 |
| `grade_prd_edit_model.py`、`build_prd_edit_review.py` | 原实际产物评分和官方静态评审页，保留模型发现的质量失败 |
| `run_model_edit_replay.py` | 当前冻结源码重放原始模型候选，修复验证不称新模型调用 |
| `test_prd_release.py` | 十个阶段 6 场景的真实生产 CLI、版本交错、同版绑定、快照冲突及中断恢复；设置 `PRD_STAGE6_EVIDENCE` 可保存新证据 |
| `prepare_prd_release_model.py`、`advance_prd_release_model.py` | 冻结阶段 6 合成输入和新旧 Skill，归档真实轮次、单独推进分析侧合成更正 |
| `grade_prd_release_model.py` | 从真实文件核对提审、确认、快照、同步及文件保护，使用 Skill Creator 生成静态人工评审页 |

代码根定位已适应分类后的目录。原始夹具、参考和认可记录仍在 `tests/fixtures/prd-generator/`、`tests/expected/prd-generator/`、`tests/results/prd-generator/`，没有重写旧哈希。

## 运行

从仓库根目录：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests/prd-generator -p 'test_*.py' -v
```

重放到不存在的新目录，不覆盖旧证据：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/prd-generator/run_prd_format_checks.py --output /path/to/new-format-trial

# 阶段4公开同步CLI：输出目录必须不存在。
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/prd-generator/run_prd_sync.py --output /path/to/new-sync-trial
```

模型对照须先有用户授权。准备阶段 6 的新目录：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/prd-generator/prepare_prd_release_model.py --output /path/to/new-model-trial
```

准备脚本不调用模型。新版和阶段 5 输入逐字节相同；只有新版在实际提问后收到测试确认，发布完成后由独立分析驱动更新一次，再由同一模型会话同步。

## 已保存证据

- [阶段 0](../results/prd-generator/stage-0.md)
- [阶段 1](../results/prd-generator/stage-1.md)
- [阶段 2](../results/prd-generator/stage-2.md)
- [阶段 3：首稿实施与试跑](../results/prd-generator/stage-3.md)
- [阶段 4：同步实施与验证进度](../results/prd-generator/stage-4.md)
- [阶段 5：实施认可](../results/prd-generator/stage-5-approval.json)、[阶段记录](../results/prd-generator/stage-5.md)、[最终评审页](../results/prd-generator/stage-5-model-review/final-03/review.html)、[最终人工认可](../results/prd-generator/stage-5-final-approval.json)：原模型与修复重放分别留证
- [阶段 4 实际输出评审页](../results/prd-generator/stage-4-model-review/final-02/review.html)
- [阶段 4 模型分析及人工评审指南](../results/prd-generator/stage-4-review-guide.md)
- [实际草稿评审页](../results/prd-generator/stage-3-model-review.html)
- [模型试跑分析](../results/prd-generator/stage-3-model-analysis.md)
- [人工试用指南](../results/prd-generator/stage-3-review-guide.md)
- [PG-29 剧本](../scenarios/prd-generator/PG-29.md)
- [格式认可](../results/prd-generator/stage-1-format-approval.json)
- [当前十五次 CLI 清单](../../workspace-sandbox/prd-generator/stage-1/attempt-02/run-manifest.json)

旧证据源码绑定当时提交，旧产物和原指纹保持；现行生产代码使用公开入口在新目录重放。接收协议留证命令与边界见 PG-29 剧本，不能把确定性重放称为新模型调用。阶段 6 的发布程序用例通过正式入口创建本地合成快照；不把合成确认当真实业务发布授权。
