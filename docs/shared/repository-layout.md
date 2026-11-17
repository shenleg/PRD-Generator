# 仓库目录与按 Skill 分类约定

本文件说明当前维护入口及历史路径边界。目录整理只改变导航和测试代码位置，不改变产品协议、安装载荷或历史证据。

## 分类规则

| 内容 | 当前位置 | 规则 |
| --- | --- | --- |
| 可安装源码 | `skill/<skill>/` | 只放生产载荷；两个 Skill 保持并列，不把文档和测试装进产品 |
| 当前维护文档 | `docs/<skill>/` | 使用 `spec.md`、`execution-plan.md` 等英文文件名；各 Skill 的 README 提供导航 |
| 共享文档 | `docs/shared/` | 写作规范、仓库结构等不属于单一 Skill 的约定 |
| 当前测试代码和重放驱动 | `tests/<skill>/` | 同组辅助模块一起移动；连字符目录使用独立 discovery，不作为普通 Python 包导入 |
| 全部测试入口 | `tests/test_all.py` | 兼容原先 `unittest discover -s tests`，汇总两组测试；导入错误不能静默跳过 |
| 跨 Skill 最小消费者 | `tools/` | 只做开发验证，不归入正式生成器产品，也不随安装分发 |
| 既有材料与证据 | `tests/fixtures/`、`expected/`、`scenarios/`、`results/` 及 `workspace-sandbox/` 原位置 | 不迁移或重写原字节；按两个 Skill 的导航查找 |
| 未来新增试跑记录 | `tests/results/<skill>/`、`workspace-sandbox/<skill>/` | 新记录写入不存在的新目录，不向历史根层继续堆叠 |

当前生成侧材料已在原资料根下使用 `prd-generator/` 分类。分析侧旧记录含较多阶段路径，保留其历史布局；分类导航不等于新复制一份数据。

文档内代码形式的仓库路径默认相对于仓库根目录；Markdown 链接相对于所在文件。历史记录的旧命令和路径代表当时环境，当前命令以根 README 及各 Skill README 为准。

## 根文档迁移

| 原位置 | 当前入口 |
| --- | --- |
| `需求分析skill-需求规格说明.md` | [分析规格](../requirement-analyst/spec.md) |
| `分阶段执行文档.md` | [分析执行计划](../requirement-analyst/execution-plan.md) |
| `INSTALL.md` | [分析安装说明](../requirement-analyst/installation.md) |
| `第二样例：仿真任务管理优化.md` | [样例说明](../requirement-analyst/sample-task-management.md) |
| `需求文档生成skill-需求规格说明.md` | [生成规格](../prd-generator/spec.md) |
| `prd-generator-execution-plan.md` | [生成执行计划](../prd-generator/execution-plan.md) |
| `分阶段执行文档写作规范.md` | [共享写作规范](staged-execution-guide.md) |

原 `tests/README.md` 的分析侧阶段说明移到 `tests/requirement-analyst/README.md`，根测试 README 现在是统一导航。原 `tests/test_prd_*.py`、`prd_fixture_support.py` 和 `run_prd_format_checks.py` 位于 `tests/prd-generator/`；其他原根层 Python 测试、辅助代码和分析重放驱动位于 `tests/requirement-analyst/`。

## 历史指纹处理

- 不修改历史 JSON、用户批准、模型输出、源码快照、日志或清单中的旧路径和旧哈希。
- 移动后的当前测试用新入口运行真实重放，不从历史副本执行当前业务代码。
- 原阶段 8 和最终验收的清单含已移动测试脚本的原路径。仅对这些测试源码从对应原验收提交读取原字节，再比对旧哈希；生产源码、夹具和业务产物继续核对当前文件，不能一律回退 Git 掩盖漂移。
- 原有阶段 2～7的历史源码策略保持原义，不重算旧指纹冒充新模型行为通过。
- 根目录 `README.md` 已修正旧的“尚未提交”等交付状态；历史报告的当时状态不倒改。最新提交与同步状态以 Git 为准。
- 原始资料、生产文件及既有证据的整理前后指纹由本次布局检查单独核对，不依赖修改旧摘要。

## 安装与运行

`.claude/skills/requirement-analyst` 仍指向 `../../skill/requirement-analyst`。`prd-generator` 仍是阶段 1 部分载荷，没有 `SKILL.md`；目录整理不安装新 Skill、不启用生成或发布，也不启动阶段 2。

统一及分组测试命令见 [测试说明](../../tests/README.md)。直接重放命令使用新的 `tests/<skill>/run_*.py` 路径；旧脚本路径不保留包装副本。
