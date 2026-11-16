# 阶段4收口与提交边界

## 当前结论

按用户最新授权，阶段4记为**当前范围完成、下游集成延期**，不再因尚未开发的下游阻塞后续研发。消费者交接、用户批准的采购模拟代验、项目安装、自动调用和同会话承接均已完成。

完整回归139项通过，0失败、0错误、0跳过。脱敏调整后的完整回归日志及汇总见 `stage-4-redacted-closure-test-run.txt`、`stage-4-closure-test-summary.json`；原先回归日志也保留，不将其改写成新一次运行。

## 安装与真实调用

- `.claude/skills/requirement-analyst` 相对链接到唯一生产目录，测试、消费者及工作区不随安装。
- `user-invocable:false`，不设置 `disable-model-invocation:true` 或 `context:fork`；Skill入口仍低于120行。
- 实际本地CLI的自然语言报修需求触发 `Skill(requirement-analyst)`；init中用户技能与斜杠菜单均不暴露它。
- 同一session续接时只回答“两个问题都选推荐A”，模型准确承接派单前可撤、派单后不可撤及先完成操作生效；原问题不重问，未采用的新推荐仍不写成事实。
- 使用Skill/Read、dontAsk、permission-prompts none，无跳过权限、无凭据或设置修改。没有新增API客户端。
- 第一条CLI命令因变长tools参数吞掉提示而失败；修正参数边界，在新证据目录成功。失败及两次成功原始输出均留在本地。用户明确授权仅入库脱敏必要证据，实际会话编号、本机路径、初始化元数据及原始诊断不提交，测试仅依赖verification.json。

详见 `INSTALL.md` 与 `workspace-sandbox/stage-4/installation/`。

## 历史证据归属

入口从调试模式改为内部模型调用后，旧模型试跑不能继续绑定当前入口冒称已重跑：阶段3源指纹改查stage-3-complete；阶段4收口前36份源码/输入快照逐份核对原指纹后保存。旧补丁、响应和指纹不改写；当前写入器仍另以原补丁重放验证。新入口的调用行为由真实CLI独立证明。

采购模拟案例来源、主会话执行方式、Q-12及completed/not_ready不因验收批准改变。消费者风险初稿也不升格为产品批准发布。

## 延期项

真实下游测试Skill尚未开发，用户明确批准延期。下游具备时补验：验收/边界/异常字段能否使用、来源标签状态及映射保留、未答事项不编造成确定预期。此项未宣称已通过，延期不阻塞阶段5。

原批准与后续收口批准分开保存：`acceptance-decision.json`、`closure-decision.json`。当前根清单状态为scoped_complete_downstream_integration_deferred。

## 本次版本操作

用户已授权提交阶段4。提交前检查.gitignore并展示变更摘要，提交后快进合并master，再从该提交新建阶段5分支。不推送；用户本次未要求标签，因此不额外创建完成标签。阶段5内容不进入阶段4提交。
