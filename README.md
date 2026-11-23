# 需求协作 Skills

先分析需求，再生成可追溯的 PRD。两个 Skill 分工独立，通过共享工作区交接。

**第一次使用？** 把 `install.py`、`skill/` 和 `offline/` 一起拷到目标机器，用已有 Python [离线安装两个 Skill](docs/prd-generator/installation.md)。无需访问 PyPI；对话使用客户端已有的模型配置。Windows 无需 WSL，也支持 macOS 和 Linux。然后用[快速上手](docs/shared/quickstart.md)的会议室预约示例练习分析、生成和变更同步，或直接看[一次真实试用的结果](docs/shared/quickstart.md#3-去哪里看结果)。

使用本地 NTFS、APFS 或 Linux 文件系统。同一工作区只在一个系统下写入，不与 WSL 或其他系统混写；详见[工作区边界](docs/prd-generator/installation.md#工作区边界)。

| Skill | 能做什么 | 从这里开始 |
| --- | --- | --- |
| `requirement-analyst` | 分析、追问和增量更新需求；接收 PRD 缺口，保留结论依据。 | [能力状态、验收证据与未验证范围](docs/requirement-analyst/README.md#能力与验收) · [生产目录](skill/requirement-analyst/) |
| `prd-generator` | 生成和同步可追溯的 PRD，处理修改分流、评审、发布门禁和定稿快照。 | [能力状态、验收证据与未验证范围](docs/prd-generator/README.md#能力与验收) · [生产目录](skill/prd-generator/) |

正式双 Skill 联调和真实试用已验收；**没有发布真实业务 PRD**。两个 Skill 的阶段编号各自独立，详细状态以各自的文档为准。

## 安装与开发

- 只使用需求分析时，见[单独安装分析 Skill](docs/requirement-analyst/installation.md#安装到其他项目)。
- [运行测试](tests/README.md)：源码回归和安装态冒烟测试（smoke）均不调用模型；模型和人工验收以各自证据为准。
- [仓库目录与历史证据约定](docs/shared/repository-layout.md) · [分阶段执行文档写作规范](docs/shared/staged-execution-guide.md) · [最小交接消费者](tools/README.md)（不是正式生成器）。

## 维护状态

每次阶段通过人工验收后，对应 Skill 维护者更新其详细状态和证据入口，仓库入口维护者核对本页摘要。历史证据保留原样，不在本页重复维护阶段明细。
