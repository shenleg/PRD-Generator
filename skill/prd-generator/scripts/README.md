# PRD 格式只读校验

本目录当前仅交付阶段 1 的格式校验，不含正式生成、编号写入、同步或发布入口。分析侧仍保持原实现；新缺口接收补丁属于阶段 2。

## 安装范围和依赖

- 当前目录是未来 `prd-generator` 的部分载荷，没有 `SKILL.md`，尚不是可调用的完整 Skill。
- 与 `requirement-analyst` 并列保留；唯一分析校验器从并列目录加载，不复制到生成侧。
- 使用 Python 3.10+ 及分析侧已有的 `scripts/requirements.txt` 依赖。当前按可信 Linux/Unix 本地工作区使用，不承诺对抗恶意并发路径替换或网络文件系统的持久化安全。
- 格式依据生成规格 §6.2、§9、§11.3；本次实际格式认可记录在仓库 `tests/results/prd-generator/stage-1-format-approval.json`，测试文件不随产品安装。

## 命令行

在仓库根目录：

```bash
uv run --offline --no-project --python /usr/bin/python3 \
  --with-requirements skill/requirement-analyst/scripts/requirements.txt \
  python -I -B skill/prd-generator/scripts/validate_prd.py /path/to/existing-requirement
```

脚本不依赖调用时目录；需求路径下必须已有 `requirement.json`、`analysis/analysis-result.json` 和 `prd/` 的正文、追溯、缺口及事件文件。不会创建需求目录或补齐文件。正文使用生成规格 §9.3 的稳定定位标记；中文标题可按模板调整。

| 可选参数 | 用途 |
| --- | --- |
| `--related-analysis PATH` | 显式提供关联分析，可重复；不扫描工作区，不读取 `analysis-report.md` |
| `--previous-trace PATH` | 显式核对历史编号保留、高水位及稳定映射身份；没有历史不声称证明编号从未复用 |
| `--numbering-patch PATH` | 只读检查待提交映射补丁的结构、已存在编号及读时版本；不分配编号 |

编号补丁仅可附加到已有工作稿校验；首次无工作稿补丁的结构可由 `numbering-patch.schema.json` 验证，实际首次分配入口留到阶段 3。

## 输出与失败

单个 JSON 含 `status` 和 `diagnostics`；诊断含 `rule`、`level`、`item_id`、`path`、`message`。退出码 `pass=0`、`warning=1`、`fail=2`，失败优先并保留适用诊断。规则编号对应生成规格 §9.9，不与上游规则编号混用；上游失败通过带“上游校验失败”的诊断明确标出。

- 缺少必需文件、非法 JSON、重复键、未知格式版本等返回失败；安装 Schema 或分析校验模块损坏直接报错，不伪装成通过。
- 待同步、未处理手工改动和 `open` 缺口按规格提示；结构、引用、不合法关闭或快照不一致仍失败。
- 缺失或不可读的辅助 `source-manifest.json` 不伪造来源清单；复用上游的结构、引用、问题、完成清单和技术规则，跳过依赖该清单的来源及历史权威性检查并显式警告，仅显示 `source_id`。此时不是完整上游 `pass`，不能借此宣称已满足发布条件。
- 已登记发布快照的两份摘要均按原始字节核对；历史追溯也用于检查编号保留。
- 校验全程只读，不修正文档、改缺口状态、分配问题或更新摘要。修正由相应维护方完成。

## 能证明什么

`pass` 证明当前输入在所执行检查范围内符合格式和可检验的一致性规则。它不证明自然语言与分析含义完全一致，也不证明缺口所引用内容足以回答原问题；这两项必须按人工参考要点评审。

当前只读校验器不实现评审/发布命令，不凭字段替用户确认。草稿和合成快照都不能因为格式通过而被称为已发布产品基线。
