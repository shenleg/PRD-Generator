# 需求协作 Skills

先分析需求，再生成可追溯的 PRD。两个 Skill 分工独立，通过共享工作区交接。

| Skill | 能做什么 | 从这里开始 |
| --- | --- | --- |
| `requirement-analyst` | 分析、追问和增量更新需求；接收 PRD 缺口，保留结论依据。 | [能力状态、验收证据与未验证范围](docs/requirement-analyst/README.md#能力与验收) · [生产目录](skill/requirement-analyst/) |
| `prd-generator` | 生成和同步可追溯的 PRD，处理修改分流、评审、发布门禁和定稿快照。 | [能力状态、验收证据与未验证范围](docs/prd-generator/README.md#能力与验收) · [生产目录](skill/prd-generator/) |

正式双 Skill 联调和真实试用已验收；**没有发布真实业务 PRD**。两个 Skill 的阶段编号各自独立，详细状态以各自的文档为准。

## 安装与开发

- [双 Skill 安装与调用](docs/prd-generator/installation.md)：并列安装两个生产目录，不安装测试、沙盒或最小消费者。只使用需求分析时，见[分析侧安装说明](docs/requirement-analyst/installation.md)。
- [运行全部测试](tests/README.md)：统一入口运行两套程序回归，不调用模型；模型和人工验收以各自证据为准。
- [仓库目录与历史证据约定](docs/shared/repository-layout.md) · [分阶段执行文档写作规范](docs/shared/staged-execution-guide.md) · [最小交接消费者](tools/README.md)（不是正式生成器）。

## 维护状态

每次阶段通过人工验收后，对应 Skill 维护者更新其详细状态和证据入口，仓库入口维护者核对本页摘要。历史证据保留原样，不在本页重复维护阶段明细。
