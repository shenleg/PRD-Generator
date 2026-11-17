# 按 Skill 运行测试

本目录将维护代码、夹具、人工参考和场景按 Skill 分类；已封存的运行证据保留原路径及字节，不修改模型记录或认可指纹。

## 入口

| 范围 | 目录或入口 | 内容 |
| --- | --- | --- |
| 全部 | `test_all.py` | 分别发现两组测试并汇总，不要求连字符目录成为 Python 包 |
| 需求分析 | [requirement-analyst/](requirement-analyst/README.md) | 分析、更新、历史、技术、体验、知识和最小交接测试，含重放驱动 |
| 文档生成 | [prd-generator/](prd-generator/README.md) | Schema、只读校验及格式证据重放 |
| 共享依赖 | `requirements.txt` | 两组共同使用的已固定依赖 |

命令从仓库根目录执行；`python -I -B` 不依赖调用者的 `PYTHONPATH`。

```bash
# 全部测试，兼容整理前的命令。
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests -p 'test_*.py' -v

# 只运行需求分析。
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests/requirement-analyst -p 'test_*.py' -v

# 只运行文档生成。
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests/prd-generator -p 'test_*.py' -v
```

全部入口依靠 `test_all.py` 的 `load_tests` 钩子；需要筛选具体文件时，请直接对对应 Skill 子目录运行 discovery，以免顶层文件名模式把统一入口也筛掉。

## 资料归属

| 资料目录 | 归属及约束 |
| --- | --- |
| `fixtures/requirement-analyst/`、`expected/requirement-analyst/`、`scenarios/requirement-analyst/` | 分析侧输入、人工参考和场景剧本 |
| `fixtures/prd-generator/`、`expected/prd-generator/`、`scenarios/prd-generator/` | 生成侧输入、人工参考和场景剧本 |
| `results/prd-generator/` | 生成侧已保存的运行记录 |
| `results/` 其他既有阶段记录 | 分析侧历史证据；保持原字节及路径，不倒改旧清单或认可记录 |
| `results/repository-layout/` | 仓库级目录整理验证，不属于产品阶段 |
| `workspace-sandbox/prd-generator/` | 生成侧合成 CLI 证据，按原清单读取 |
| `workspace-sandbox/stage-*`、`workspace-sandbox/final-acceptance/` | 分析侧历史模型及 CLI 证据，保持原位置 |

未来新增记录按 `tests/results/<skill>/` 分类，未来新试跑按 `workspace-sandbox/<skill>/` 分类，不倒改旧证据。跨 Skill 的最小消费者保留在 `tools/`，它是分析交接的开发验证工具，不是假装已完成的正式生成器。

历史文档里的旧 `tests/run_*.py` 是当时路径；当前重放命令以各 Skill 的 README 为准。不保留一排同名旧脚本包装，避免重新把根目录堆满。
