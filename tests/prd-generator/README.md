# PRD Generator 测试

本目录收纳生成 Skill 的 Schema、只读 PRD 校验及格式证据测试。只检查阶段 1 格式，不证明正式生成、缺口接收或发布能力已实现。

## 维护代码

| 文件 | 用途 |
| --- | --- |
| `test_prd_schemas.py` | 三份 Schema 的结构、兼容与严格补丁边界 |
| `test_prd_validation.py` | 十二条规则、正文定位、引用、缺口、快照及只读边界 |
| `test_prd_format_runs.py` | 保存证据的来源和产物指纹、实际响应及新目录重放 |
| `prd_fixture_support.py` | 构造注明合成的独立临时夹具 |
| `run_prd_format_checks.py` | 在新目录运行十五次真实只读校验并保留证据 |

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
```

## 已保存证据

- [阶段 0](../results/prd-generator/stage-0.md)
- [阶段 1](../results/prd-generator/stage-1.md)
- [格式认可](../results/prd-generator/stage-1-format-approval.json)
- [当前十五次 CLI 清单](../../workspace-sandbox/prd-generator/stage-1/attempt-02/run-manifest.json)

生产载荷及其指纹未变；当前测试使用新入口重放，不能把目录整理或确定性重放称为新模型调用。当前没有正式发布器，合成快照确认不是真实发布授权。
