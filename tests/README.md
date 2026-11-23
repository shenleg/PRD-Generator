# 按 Skill 运行测试

本目录将维护代码、夹具、人工参考和场景按 Skill 分类；已封存的运行证据保留原路径及字节，不修改模型记录或认可指纹。

## 入口

| 范围 | 目录或入口 | 内容 |
| --- | --- | --- |
| 全部 | `test_all.py` | 分别发现两组 Skill 测试并汇总，不要求连字符目录成为 Python 包 |
| 安装器 | `requirement-analyst/test_install.py` | 验证项目路径、依赖隔离和失败回滚，不联网 |
| 安装态 smoke | [`prd-generator/run_installed_smoke.py`](prd-generator/run_installed_smoke.py) | 验证已安装的双 Skill 程序链；单独运行，不进入默认测试发现 |
| 需求分析 | [requirement-analyst/](requirement-analyst/README.md) | 分析、更新、历史、技术、体验、知识和最小交接测试，含重放驱动 |
| 文档生成 | [prd-generator/](prd-generator/README.md) | Schema、只读校验及格式证据重放 |
| 共享依赖 | `requirements.txt` | 两组共同使用的已固定依赖 |

命令从仓库根目录执行；`python -I -B` 不依赖调用者的 `PYTHONPATH`。

## Linux 源码回归

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

全部入口依靠 `test_all.py` 的 `load_tests` 钩子；需要筛选具体文件时，请直接对对应 Skill 子目录运行 discovery，以免顶层文件名模式把统一入口也筛掉。历史全量回归以 Linux 记录为准。

## 安装态 smoke

在 Windows PowerShell、macOS 或 Linux 上，用本机 Python 3.10+ 单独运行。让项目和系统临时目录都位于受支持的[本地文件系统](../docs/prd-generator/installation.md#工作区边界)。两种模式选其一：

- `--install`：调用 `install.py`，仅用随包 wheel 在临时项目完成一次真实的离线安装，可在无外网且无 pip 缓存的机器运行。
- `--installed-project PROJECT`：复用已用安装器装好两个 Skill 和共用环境的项目；不安装依赖，业务写入只发生在临时合成工作区。

**Windows（PowerShell，无需 WSL）**：

```powershell
py -3 -I -B tests/prd-generator/run_installed_smoke.py --install
py -3 -I -B tests/prd-generator/run_installed_smoke.py --installed-project "C:\path\to\target-project"
```

没有 `py` 启动器时，改用指向本机 Python 3.10+ 的 `python`。

**macOS / Linux**：

```bash
python3 -I -B tests/prd-generator/run_installed_smoke.py --install
python3 -I -B tests/prd-generator/run_installed_smoke.py --installed-project "/path/to/target-project"
```

Smoke 从与仓库和安装项目无关的目录调用已安装的脚本，验证首次分析保存、PRD 事件写入中断后的恢复，以及同版本并发提交只有一方成功。它不调用模型，不验证真实业务发布或断电。

平台专项验收从仓库根目录、用**已装依赖的解释器**分别执行以下脚本（例如用目标项目安装器返回的 Python，传入 `-I -B` 和脚本路径）：

- [`tests/requirement-analyst/test_portable_fs.py`](requirement-analyst/test_portable_fs.py)：检查锁竞争、进程退出后的释锁、平台链接和二进制读写。Windows junction 用例须在原生 NTFS 上运行。
- [`tests/prd-generator/test_native_transactions.py`](prd-generator/test_native_transactions.py)：恢复带反斜杠的旧事务日志，验证重复恢复不重复追加事件，并检查只读快照和同名冲突清理。

这些命令可在三端复跑；Wine 下运行 Windows 版 Python 不替代原生 NTFS 或 APFS 验收。

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
