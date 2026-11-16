# 分析结果校验器

本目录提供只读校验器，供分析过程和下游共同使用；不会改写分析文件、分配编号或更新工作区。规则依据为需求规格 9.6。

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

## 自动回归

```bash
uv run --with-requirements tests/requirements.txt \
  python -I -m unittest discover -s tests -p 'test_*.py' -v
```

持久反例及期望规则位于 `tests/fixtures/invalid/`；运行记录和格式评审位于 `tests/results/`。这些内容不随 Skill 安装。
