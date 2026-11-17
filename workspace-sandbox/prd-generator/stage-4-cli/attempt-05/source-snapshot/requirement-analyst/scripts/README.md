# 分析校验与补丁写入

本目录提供唯一只读校验器 validate_analysis.py，以及负责正式写入、编号、事件和并发保护的 update_analysis.py。校验规则依据规格 9.6，补丁协议及恢复边界见 ../references/incremental-update.md。校验器始终只读，只有更新器写分析业务文件；索引器仅维护项目index/，save_knowledge.py仅在具体批准后新建knowledge/文件，其余资料工具只读业务数据。

## 安装与运行

需要 Python 3.10 或更新版本。在仓库根目录执行：

```bash
uv run --with-requirements skill/requirement-analyst/scripts/requirements.txt \
  python -I skill/requirement-analyst/scripts/validate_analysis.py \
  tests/fixtures/high-low-voltage/analysis-result.json
```

默认读取结果旁边的 `source-manifest.json`，以及当前需求存在的 `../prd/gap-requests.json`。来源清单不在同一目录时，用 `--source-manifest PATH` 指定；独立缺口夹具可用 `--gap-requests PATH` 显式提供。校验器只读，问题接收关联须在本需求缺口中存在且唯一；旧问题没有 `gap_request_ref` 仍合法。

跨需求引用需要显式提供目标分析文件：

```bash
python -I skill/requirement-analyst/scripts/validate_analysis.py analysis-result.json \
  --related-analysis /path/to/other/analysis-result.json
```

`--related-analysis` 可重复，每份外部结果读取其相邻的来源清单。脚本不自动搜索工作区，也不访问网络。

## 输出与退出码

标准输出只有一个 JSON 对象，包含 `status` 和 `diagnostics`。诊断包含规则编号 `rule`、级别 `level`、条目编号 `item_id`、位置 `path` 和原因 `message`；无条目编号时使用 `$`。

| status | 退出码 | 下游行为 |
| --- | --- | --- |
| `pass` | 0 | 数据合法，仍须读取 `meta.readiness` 决定草稿用途 |
| `warning` | 1 | 显示过期警告，按规格 10.2 处理 |
| `fail` | 2 | 不得使用，按诊断修正后重验 |

`not_ready` 不等于校验失败；它可以是如实保留 P0 缺口的合法结果。技术评估省略不等于已评估为无风险。多个问题同时存在时保留全部诊断，失败优先于警告。脚本不替用户回答问题，也不判断自然语言业务内容是否充分。

## 应用补丁

更新器使用标准库 fcntl 和目录 fsync，当前支持 Linux/Unix 本地工作区；未验证 Windows 或网络文件系统的锁与持久化语义。运行锁、恢复记录和中断残留留在本地，不作为业务产物交付。

```bash
uv run --no-project --python /usr/bin/python3 \
  --with-requirements skill/requirement-analyst/scripts/requirements.txt \
  python -I -B skill/requirement-analyst/scripts/update_analysis.py \
  --workspace workspace-sandbox/my-workspace --project demo --patch patch.json
```

可先加 `--dry-run` 预检；`--related-analysis PATH` 可重复指定关联分析。补丁使用 `patch_version: "1.0"`、读取时的 `base_revision` 和临时别名；详见补丁协议，不接受整份 analysis-result 替换。正式结果、来源、事件由脚本维护；报告由分析者根据保存后的 JSON 整理。

输出仍为 pass/warning/fail，额外含 requirement_id、revision、id_map、affected_ids、written。warning 可保存 stale，但必须向用户提示；校验失败不提交候选分析，revision 冲突须重新读取。首次分配需求目录并写 common；后续保留 requirement.json 和 inputs/。常规更新不写 prd/；缺口接收成功后唯一例外是标记对应缺口状态，细则见 `../references/incremental-update.md` 的“接收 PRD 缺口”。标记失败可返回 fail 且 written=true，代表分析已提交、缺口尚待重读重试；`gap_status_written` 仅表示本次是否实际改动状态。重复接收复用已有问题，纯重复不推进修订。工作区独占锁及写前记录用于恢复中断，不等于面向任意读取者的跨文件原子快照。

API `update_analysis(workspace, project_id, patch, *, related_analyses=(), dry_run=False)` 返回同一响应对象。输入补丁及关联资料不被修改；用户协议/文件错误给结构化 fail，内部 Schema 安装错误直接抛出。

## 历史资料工具（阶段5）

```bash
python -I -B scripts/compare_baseline.py --baseline OLD/analysis-result.json --proposal NEW/analysis-result.json
python -I -B scripts/compare_baseline.py --check-sources ANALYSIS/analysis-result.json --project-root PROJECT_ROOT
python -I -B scripts/index_sources.py --project-root PROJECT_ROOT --catalog catalog.json
python -I -B scripts/search_project.py --project-root PROJECT_ROOT --query "用户 删除" --limit 5 --max-chars 2000
```

上例从Skill目录执行；其他cwd用脚本绝对路径，解释器须装本目录requirements.txt依赖。全部输出单JSON和0/1/2状态。compare输入旁须有source-manifest，跨需求结果以--related-analysis重复显式提供；它不是自然语言冲突裁决器、不修改基线。--check-sources只返回重评候选，分析状态须经补丁保存。

catalog为来源清单数组：source_id/name/path/type/credibility/last_updated/revision，path为项目根内相对普通UTF-8文本；可附requirement_id/module/tags/terms/authority/publication_basis。默认authority=unconfirmed，当前发布或正式规范必须有发布依据。资料最后业务更新时间采用YYYY-MM-DD或null，不从mtime推定。adopted_sha256是分析采用字段，不是catalog输入字段；索引计算自己的sha256。

索引只写index/project-index.json及source-index.json，使用工作区锁；两文件世代不一致时fail，重新索引恢复，不删用户资料。检索按query空白分词后casefold子串匹配（任一关键词），元数据过滤是大小写不敏感精确匹配；不进行语义检索。结果results含来源路径、行location、版本、权威、指纹和限定excerpt。变动来源进stale_sources且正文被排除，刷新索引后再读。

检索默认5条/摘要共2000字符，最多20条/20000字符；单次读取最多64文件/2MiB、单文件1MiB，任何截断会提示。使用--requirement/--module/--tag/--term缩小范围；--as-of与--max-age-days控制业务年龄复核，默认365天。没有资料/没有命中不是无冲突。非空分析事务阻止操作；已完成null日志允许，路径符号链接被拒。只支持可信本地进程遵锁的工作区，不保证恶意并发中间目录换链安全。

历史采用、旧版本归档、显式基线登记与语义分析规则见 `../references/historical-retrieval.md`。1.0增加选填history_review和来源字段，旧结果继续合法，不迁移、不将旧草稿默认为发布基线。

## 受控知识沉淀

`save_knowledge.py --project-root PROJECT_ROOT --proposal PROPOSAL.json --approval APPROVAL.json`仅在用户或指定负责人批准准确条目后新建知识文件，不覆盖既有知识、不写analysis/、不自动索引。完整建议指纹、资格/来源核验、批准记录及失败保留现场规则统一见`../references/domain-knowledge.md`。它不验证确认者身份或代替业务事实核实；程序测试中的合成approve不构成实际批准。

## 自动回归

```bash
uv run --with-requirements tests/requirements.txt \
  python -I -m unittest discover -s tests -p 'test_*.py' -v
```

持久反例及期望规则位于 `tests/fixtures/invalid/`；运行记录和格式评审位于 `tests/results/`。这些内容不随 Skill 安装。
