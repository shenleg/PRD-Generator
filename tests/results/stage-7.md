# 阶段7验收：体验与视觉分析

## 结论

**阶段7已按用户批准的合成页面资料范围完成，RA-22、RA-23验证通过。** 完整回归 **195项通过，0失败、0错误、0跳过**。

实际安装Skill能自动按需加载体验参考并读取PNG图像；区分画面能证明的事实、未展示信息和候选设计。缺视觉稿时建议最小必要资料，不假设完整界面；普通后端不要求视觉稿。核心选择范围、重复生效、部分成功后取消及统计口径仍归产品P0，而不是样式待办。

当前分支`feat/stage-7-ux-visual`，HEAD仍为阶段6提交`6fcf4bb`。**未提交、未合并、未推送、未打标签，未进入阶段8。** 阶段4延期的真实下游Skill集成仍延期。

合成静态参考不等于真实系统、点击交互验证、用户研究或设计签核。六个case共享一次实际模型上下文；模型生成四字段、观察/页面候选及问题，业务骨架/完成清单/readiness由驱动器提供，不冒称完整业务需求端到端自主分析。

## 已实现

- 新增ux-visual-assessment.md：按页面、数据展示、复杂流程/状态、后端分型；资料和图像范围、状态/反馈检查、设计建议及核心业务分工。
- Skill新增体验按需指针、更新能力边界，保持55行；没有打开独立斜杠入口，不fork当前对话。
- 复用ux_assessment既有四字段及可追溯业务条目：ui_dependent、design_pending_items、visual_recommendations、interaction_flows。Schema、更新器和校验器均未修改，schema_version仍1.0。
- 观察事实限定本张截图，建议页面/候选流程明确proposed/inferred；来源与定位保留。PNG直接作为明确输入看图，不声称UTF-8检索器能解析图片。
- 修复消费者遗漏ux_assessment，草稿原样保留体验判断和设计不确定性；报告不再误称“仅作界面判断/未开展视觉分析”。两处均先写测试实际失败，再修复通过。
- 阶段6历史源码与模型证据绑定已提交6fcf4bb，不改旧哈希冒充新体验行为；当前工具仍重放所有旧场景。

## 图像及本地浏览器验证

构造的reference-list.html是**静态低保真资料**，不是完整产品前端，没有撤回业务代码、后台接口、确认弹窗或隐藏状态。实际生成1360×900的reference-list.png，主会话用Read实际查看，画面正常，无空白/缺字或错误页。页面清楚标“合成低保真参考·非真实系统”，只展示列表常态。

浏览器过程保留事实：

1. Playwright MCP因root环境Chromium沙箱启动失败，没有得到页面。
2. 备用headless no-sandbox命令被安全保护拒绝，未执行；没有换工具或代理绕过。
3. 向用户说明，用户明确选择“授权本次本地截图”。仅此次用独立临时配置访问127.0.0.1自建静态页面截图，不用既有账号、不改全局配置，不扩大到外网或其他操作。
4. 截图完成后实际看图，本地HTTP服务已停止。临时浏览器配置留本地，不自动删除用户文件。

授权及生成记录：workspace-sandbox/stage-7/browser-capture.json。该授权不是未来浏览器操作关闭沙箱的一般许可。

## 实际模型与六个场景

实际CLI以普通需求分析任务自动调用requirement-analyst，按需读取ux-visual-assessment，Read PNG工具返回图像载荷。**模型没有读取HTML源码**，也没有读取测试期望、旧试跑或测试代码。只保存必要脱敏工具轨迹与结构化输出，不保存原始会话、实际session编号、初始化元数据或图片base64。

| case | 实际结果与独立核对 | 结论 |
| --- | --- | --- |
| UX-MISSING（RA22） | 复杂多角色工作台无资料：ui=true、观察为空，仅候选页面；建议角色流程/状态和低保真，不强制高保真。权限、混批、重提为产品P0。 | pass |
| UX-BACKEND（RA23） | 纯内部接口：ui=false，观察/页面/待设计为空，无ask_design或视觉索取。接口非法输入/研发核查仍正常登记，不因无界面强行零问题。 | pass |
| UX-REFERENCE | 看到工作台标题、当前用户、列表筛选/表头/状态/查看，未见批选入口；只认截图呈现，不推后台授权。选择范围/跨页/重复/执行时变化为产品P0。 | pass |
| UX-CLAIM | “沿用现有批量按钮和弹窗”的说法未被常态图支持：登记lookup及补图建议，不直接断言全系统没有；重试对象和重复生效为产品P0。 | pass |
| UX-STATES | 选中/执行中/部分失败等仅待设计；已部分成功后取消和批次身份/超时规则保留产品P0，不当按钮样式。 | pass |
| UX-DATA | 无图无数据字典：指标/时间/统计明细范围/刷新/异常口径均产品P0；不自定图表类型、口径或制作可视化。 | pass |

第一例、第三至第六例not_ready，第二例因保留未答产品P1为conditionally_ready。未提供任何模拟产品答案，没有为验收关闭问题。

## 保存及交接

run_stage_7_trial只机械映射实际输出：

- 四个ux字段逐项原样保存。
- 画面观察写入现有boundaries且带PNG SRC和画面位置；页面清单用scenarios，observed为confirmed且仅指本图，proposed为inferred和建议文字。
- 问题正文、优先级、责任方、选项和推荐均保留，新增ID由更新器分配。
- 没有截图的case观察为空，不从其他case偷借图像。
- 业务目标/功能骨架及完成清单由合成驱动器提供，不作为完整真实业务充分性证明。

六份结果通过实际更新器保存，再各自独立运行唯一校验器，通过后生成13章报告和消费者草稿。**18次实际CLI调用：12pass、6warning**，warning均为未决问题带来的限定用途草稿，不代表失败也不表示业务已就绪。

6份报告、6份草稿及136份场景产物有指纹。消费者前后分析JSON、来源、事件、报告原字节一致；草稿明确“视觉建议不是已确认界面或已实现行为”。

## 测试及复核入口

新增11项：9项保存的图像/语义/来源/权限/报告/重放检查，1项消费者体验遗漏回归，1项报告旧说明回归。此前184项全部继续通过，最终195项。

- 主验收：tests/results/stage-7-validation.json。
- 测试汇总与日志：stage-7-test-summary.json、stage-7-test-run.txt。
- 实际模型输出：workspace-sandbox/stage-7/model-attempt-01/verification.json。
- 实际脚本工作区、补丁、退出码、报告/草稿：workspace-sandbox/stage-7/attempt-01/。
- 索引入口：workspace-sandbox/stage-7/run-manifest.json。

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests -p 'test_*.py' -v
```

重放到**不存在的新目录**，不重新调用模型或浏览器：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B tests/run_stage_7_trial.py --output /tmp/new-stage7-trial \
  --model-evidence workspace-sandbox/stage-7/model-attempt-01/verification.json
```

## 未做与后续边界

没有开发实际采购应用，没有实现批量业务、状态机或后台权限，没有新增统计图表、高保真原型或设计签核。截图未覆盖的按钮、点击行为、加载/空/错等状态均不能由本次验证推定已存在或已正确。

体验分析建议的可信度受资料范围限制，不能代替真实用户可用性测试。资料未提供时降级，不让缺图阻断基本需求分析；核心业务未定仍需产品确认，实际视觉设计由负责方后续完成。

本次不提交、不推送或进入阶段8，阶段8仍需独立确认负责人及知识沉淀机制。
