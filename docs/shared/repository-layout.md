# 仓库目录与按 Skill 分类约定

本文件说明当前维护入口及历史路径边界。目录整理只改变导航和测试资料位置，不改变产品协议、安装载荷或历史证据。

## 分类规则

| 内容 | 当前位置 | 规则 |
| --- | --- | --- |
| 可安装源码 | `skill/<skill>/` | 只放生产载荷；两个 Skill 保持并列，不把文档和测试装进产品 |
| 当前维护文档 | `docs/<skill>/` | 使用 `spec.md`、`execution-plan.md` 等英文文件名；各 Skill 的 README 提供导航 |
| 共享文档 | `docs/shared/` | 写作规范、仓库结构等不属于单一 Skill 的约定 |
| 当前测试代码和重放驱动 | `tests/<skill>/` | 同组辅助模块一起维护；连字符目录使用独立 discovery，不作为普通 Python 包导入 |
| 测试输入夹具 | `tests/fixtures/<skill>/` | 按 Skill 分类；既有原文、黄金结果、来源清单及图片只移动，不改原字节 |
| 人工参考要点 | `tests/expected/<skill>/` | 按 Skill 分类；已获认可的正文保留原字节和认可范围 |
| 场景剧本 | `tests/scenarios/<skill>/` | 按 Skill 分类；当前导航路径同步更新，不改变输入含义、预设回答或判分依据 |
| 全部测试入口 | `tests/test_all.py` | 兼容原先 `unittest discover -s tests`，汇总两组测试；导入错误不能静默跳过 |
| 跨 Skill 最小消费者 | `tools/` | 只做开发验证，不归入正式生成器产品，也不随安装分发 |
| 已封存运行证据 | `tests/results/`、`workspace-sandbox/` 原位置 | 不迁移或重写历史日志、清单、用户批准、模型输出及业务快照 |
| 未来新增试跑记录 | `tests/results/<skill>/`、`workspace-sandbox/<skill>/` | 新记录写入不存在的新目录，不向历史根层继续堆叠 |

两个 Skill 的夹具、参考要点和场景均有独立子目录，不再以“根层默认为分析侧”区分归属。仓库级布局验证记录位于 `tests/results/repository-layout/`，不归属于任何产品阶段。

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

## 测试资料迁移与历史指纹

- 原分析侧 `tests/fixtures/<资料>`、`tests/expected/<资料>`、`tests/scenarios/<剧本>` 分别移入对应 `requirement-analyst/` 子目录；生成侧 `prd-generator/` 资料不动。逐文件路径、原指纹和场景导航改动见 `tests/results/repository-layout/test-materials/migration.json`。
- 已认可参考正文和来源清单中的旧路径保留为历史来源标识，不因搬迁重新签署认可或重算旧哈希。查找这些资料时，在原资料根后插入 `requirement-analyst/`；原根文档路径按上表查找。
- 不修改历史 JSON、用户批准、模型输出、源码快照、日志或清单中的旧路径和旧哈希。
- 当前重放驱动使用新资料路径，新运行清单记录新路径；不从历史副本执行当前业务代码。
- 原阶段 8 和最终验收清单中的已移动测试源码，仍从对应原验收提交读取原字节并比对旧哈希。生产源码、夹具和业务产物继续核对当前文件，不能一律回退 Git 掩盖漂移。
- `tests/requirement-analyst/material_paths.py` 仅按逐文件迁移表解析历史资料路径。资料缺失或内容变化仍使读取或原哈希校验失败，不回退旧位置或 Git 副本；不重映射生成侧或未知路径。
- 原有阶段 2～7 的历史源码策略保持原义，不将旧路径转换后交给 Git，不重算旧指纹冒充新模型行为通过。
- 历史报告的当时状态不倒改；最新提交与同步状态以 Git 为准。整理前后的产品文件及既有证据指纹单独核对，不依赖修改旧摘要。

## 安装与运行

仓库内的 `.claude/skills/requirement-analyst` 指向 `../../skill/requirement-analyst`；现行 `prd-generator` 生产入口位于 [`skill/prd-generator/SKILL.md`](../../skill/prd-generator/SKILL.md)。在其他项目使用时按[双 Skill 安装说明](../prd-generator/installation.md)并列安装。历史目录整理的记录只说明当时的安装状态。

统一及分组测试命令见 [测试说明](../../tests/README.md)。直接重放命令使用新的 `tests/<skill>/run_*.py` 路径；旧脚本和旧资料路径不保留包装副本或兼容符号链接。
