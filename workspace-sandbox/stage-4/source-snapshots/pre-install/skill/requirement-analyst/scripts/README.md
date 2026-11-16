# 分析校验与补丁写入

本目录提供唯一只读校验器 validate_analysis.py，以及负责正式写入、编号、事件和并发保护的 update_analysis.py。校验规则依据规格 9.6，补丁协议及恢复边界见 ../references/incremental-update.md。校验器始终只读，只有更新器写入工作区。

## 安装与运行

需要 Python 3.10 或更新版本。在仓库根目录执行：

```bash
uv run --with-requirements skill/requirement-analyst/scripts/requirements.txt \
  python -I skill/requirement-analyst/scripts/validate_analysis.py \
  tests/fixtures/high-low-voltage/analysis-result.json
```

默认读取结果旁边的 `source-manifest.json`。来源清单不在同一目录时，用 `--source-manifest PATH` 指定。

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

输出仍为 pass/warning/fail，额外含 requirement_id、revision、id_map、affected_ids、written。warning 可保存 stale，但必须向用户提示；fail 不写候选业务文件，revision 冲突须重新读取。首次分配需求目录并写 common；后续保留 requirement.json、inputs/ 和 prd/。工作区独占锁及写前记录用于恢复中断，不等于面向任意读取者的跨文件原子快照。

API `update_analysis(workspace, project_id, patch, *, related_analyses=(), dry_run=False)` 返回同一响应对象。输入补丁及关联资料不被修改；用户协议/文件错误给结构化 fail，内部 Schema 安装错误直接抛出。

## 自动回归

```bash
uv run --with-requirements tests/requirements.txt \
  python -I -m unittest discover -s tests -p 'test_*.py' -v
```

持久反例及期望规则位于 `tests/fixtures/invalid/`；运行记录和格式评审位于 `tests/results/`。这些内容不随 Skill 安装。
