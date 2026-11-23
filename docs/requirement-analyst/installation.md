# 安装与调用

交付导航见根`README.md`，阶段1～8范围及最终验收见`tests/results/final-acceptance.md`。最终收口另核对完整安装载荷，并从其他cwd实际运行安装路径的校验CLI；这不等于重新执行模型自动调用测试。

## 当前仓库

当前项目通过 `.claude/skills/requirement-analyst` 相对符号链接安装，唯一源码位于 `skill/requirement-analyst/`。POSIX 系统正常检出 Git 符号链接后即可发现，不复制第二份源码；`tests/`、`tools/` 和试用工作区不随 Skill 安装。

入口设置 `user-invocable: false`，因此不提供 `/requirement-analyst` 命令；普通需求分析场景仍可由模型自动调用。未禁用模型调用，也未设置 `context: fork`，沿用当前会话已有信息。安装后需启动新会话发现，不能仅凭当前旧会话列表判断未安装。

## 安装到其他项目

优先用 `install.py` [一键安装两个 Skill 和共用依赖](../prd-generator/installation.md#安装到新项目或隔离试用项目)。只需需求分析时，可手动安装 `requirement-analyst`：

1. 将本仓库的 `skill/requirement-analyst/` 完整复制到目标项目的 `.claude/skills/requirement-analyst/`。macOS 和 Linux 也可链接整个生产目录。先核对同名目标，不覆盖现有安装；Windows 按复制路径安装，不依赖仓库的符号链接。
2. 确认 `.claude/.prd-skills-venv/` 不存在后，从目标项目目录用 Python 3.10+ 执行对应命令。已有环境时，先核对其用途和依赖，不另行覆盖。

   **Windows（PowerShell，本机 Python）**：

   ```powershell
   $bundle = 'C:\path\to\offline'  # 随安装包提供的 offline 目录
   py -3 -m venv .claude/.prd-skills-venv
   $env:PIP_CONFIG_FILE = 'NUL'
   & ".\.claude\.prd-skills-venv\Scripts\python.exe" -m pip --isolated --disable-pip-version-check install --no-index --only-binary=:all: --require-hashes --find-links "$bundle\wheels" -r "$bundle\requirements.lock"
   ```

   没有 `py` 启动器时改用指向本机 Python 3.10+ 的 `python`。

   **macOS / Linux**：

   ```bash
   bundle='/path/to/offline'  # 随安装包提供的 offline 目录
   python3 -m venv .claude/.prd-skills-venv
   PIP_CONFIG_FILE=/dev/null .claude/.prd-skills-venv/bin/python -m pip --isolated --disable-pip-version-check install \
     --no-index --only-binary=:all: --require-hashes --find-links "$bundle/wheels" -r "$bundle/requirements.lock"
   ```

3. 在目标项目打开新会话，通过自然语言触发分析。运行脚本直接用上述虚拟环境的解释器，无需激活。

虚拟环境不随项目提交；若 Python 未自动生成环境内的 `.gitignore`，请将 `.claude/.prd-skills-venv/` 加入目标项目的忽略规则。只装分析侧也遵守同样的[本地工作区边界](../prd-generator/installation.md#工作区边界)。

## 阶段 4 安装验证（历史）

使用已安装的本地 Claude Code 2.1.325，通过普通“内部报修撤回需求”提示启动真实 CLI：

- 模型实际调用 `Skill(requirement-analyst)`，从项目安装路径读取按需参考文件。
- init 的用户技能与斜杠命令列表均未暴露该技能；这与 `user-invocable: false` 一致，不表示模型无法发现。
- 续接同一 session，仅输入“两个问题都选推荐 A”，实际正确承接“派单前可撤”和“先完成操作生效”，没有重复追问这两个已回答规则。
- 仅启用 Skill/Read，权限模式 dontAsk，无人可回答的权限提示直接拒绝；没有跳过权限、修改设置或读取凭据。
- 第一条命令因变长 `--tools` 吃掉提示参数而失败，已保留；修正为用 `--` 分隔提示参数后，新尝试通过。

入库证据：`workspace-sandbox/stage-4/installation/verification.json`。用户明确授权仅提交脱敏证据，已去除实际会话编号、本机绝对路径和无关初始化元数据；保留必要工具调用、相对参考路径和模拟业务回答。同会话用文件内别名关联，原始输出与诊断留本地、由.gitignore排除。测试只读取可入库证据，不依赖本地原始会话，也不重新调用模型。

参考官方文档：

- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/cli-reference

## 阶段5的当前安装验证

生产入口仍通过同一相对链接安装。历史能力接入后，另以自然语言的新旧删除规则对照提示运行真实CLI：实际自动调用requirement-analyst，按需读取historical-retrieval.md，并识别有未完成任务用户的删除提议与现行规则冲突，保留产品待决问题，不写基线。最小脱敏证据见 `workspace-sandbox/stage-5/installed-skill-verification-02.json`；原阶段4证据绑定原提交，未重写其哈希来冒充阶段5新行为。

## 阶段6的技术评估调用

当前生产入口新增feasibility-assessment渐进引用。通过实际CLI只读评估合成技术需求，自动调用Skill并读取技术参考；资料充足时限定范围判断，缺资料/旧草稿/部分证明保持unknown，核心业务取舍仍登记产品问题。最小脱敏证据及明确的定点重评范围见 `workspace-sandbox/stage-6/run-manifest.json`，没有新API客户端或原始会话记录入库。

## 阶段7的体验与图像调用

当前安装入口新增ux-visual-assessment按需引用。实际CLI调用Skill并读取1360×900合成PNG（图像载荷返回已核对），未读取HTML源码替代看图；六个case覆盖缺视觉稿、纯后端、已有列表、说法未被图支持、异步状态及数据口径未定。必要脱敏记录见 `workspace-sandbox/stage-7/run-manifest.json`；不存原始模型会话或图片base64，不将截图当真实系统或点击验证。

下游测试 Skill 尚未开发，仍按用户批准延期集成验证；它不是安装本分析 Skill 或完成阶段5/6/7的前提。

## 阶段8的受控知识沉淀

生产入口按需读取`references/domain-knowledge.md`，`scripts/save_knowledge.py`随完整Skill目录安装，复用现有Python依赖和路径/锁工具。只有实际用户或指定负责人明确批准具体建议后才调用；脚本不做身份认证，不自动把分析结论写入长期知识。默认只新建，不覆盖，不自动更新索引。

本次在独立分支开发，使用合成资料及主会话逐项人工批准机制。展示准确正文、范围和目标后，用户实际选择“批准 DK-001”，已执行写入、核验、不覆盖验证及显式索引检索。公开CLI测试不调用模型，未新做安装自动触发或独立盲测；实际证据见`workspace-sandbox/stage-8/run-manifest.json`，验收范围见`tests/results/stage-8.md`。
