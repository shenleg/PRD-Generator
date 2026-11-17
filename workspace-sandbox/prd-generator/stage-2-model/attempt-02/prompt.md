# 实际模型行为试跑输入

请使用本次隔离的 Requirement Analyst Skill 处理以下请求。Skill 路径是本文件旁的 `skill-snapshot/requirement-analyst/SKILL.md`，工作区是本文件旁的 `workspace/`，项目为 `demo`，需求为 `MODEL-TASK`。关联资料明确提供为 `workspace/projects/demo/requirements/MODEL-RELATED/analysis/analysis-result.json`，可用于核验引用。

用户请求：PRD 回交了几个缺口，请先接收登记，保留已有分析结果和未解决问题。这轮不要替我回答缺口，也暂不继续业务追问；告知分别需要谁确认。不要生成、修改或发布 PRD。

请先读 Skill 入口，按路由处理。实际通过公开更新脚本保存，不直接编辑业务 JSON。把实际候选补丁放在本目录的 `candidate.patch.json`；保存脚本响应为 `update-response.json`、退出码为 `exit-code.txt`，把面向用户的答复保存为 `model-response.md`。若执行校验/预检，也保存真实输出。运行 Python 使用隔离模式，依赖可以使用仓库固定的 uv 命令。不得修改 Skill、生产代码或测试，不得读取参考答案、历史模型输出或其他试跑目录。
