# 阶段 1 校验场景

本文描述机械校验用例，不替代已由用户审核的业务参考要点。输入基于黄金样例的合成变体，均不需要用户回答。

## 输入与预设回答

基准输入为 `fixtures/high-low-voltage/analysis-result.json` 及邻接来源清单。用户回答：不适用；测试不得把合成的回答或决策写回黄金样例。

| 场景 | 输入变化 | 预期 |
| --- | --- | --- |
| V-01 | 删除必填节，或使用错误的容器类型 | fail，规则 1 |
| V-02 | 重复条目/来源编号，或引用不存在的编号 | fail，规则 2 |
| V-03 | 使用非法枚举 | fail，规则 3 |
| V-04 | 有 open P0、未处理矛盾或无有效假设的产品 P1，却声明 ready | fail，规则 4 |
| V-05 | provisional 问题没有 active 假设 | fail，规则 5 |
| V-06 | excluded P0 没有 active 决策 | fail，规则 6 |
| V-07 | active 条目没有来源、来源编号不存在或清单格式非法 | fail，规则 7 |
| V-08 | 有效条目/未废弃问题引用已撤销条目 | fail，规则 8 |
| V-09 | 非 unknown 技术结论缺少依据、来源、可信程度或影响，或引用非研发问题 | fail，规则 9 |
| V-10 | 矛盾关联不存在的问题 | fail，规则 10，可同时出现规则 2 |
| V-11 | 合法结果的分析状态为 stale | warning，规则 11 |

## 正向与交互边界

- [ ] 黄金样例 pass，但仍为 not_ready，三个 P0 仍 open。
- [ ] 产品 P1 可 conditionally_ready；有 active 假设后可 ready。
- [ ] ask_dev 的 P1 不单独阻塞 ready。
- [ ] 已撤销/待重评的假设、决策不能关闭问题。
- [ ] 已撤销矛盾不阻塞；已解决问题关联的矛盾不阻塞。
- [ ] to_reassess 条目可以保留到 withdrawn 条目的旧引用；dropped 问题可以保留旧引用。
- [ ] 省略技术评估、unknown 空依据合法；有依据的非 unknown 结论合法。
- [ ] 跨需求引用有显式目标资料时通过，缺资料或目标编号时失败。
- [ ] stale 与结构或一致性错误同时出现时，保留警告但整体 fail。
- [ ] CLI 分别返回 0、1、2；坏 JSON、缺文件、缺来源清单返回明确诊断。
- [ ] API 和 CLI 都不修改输入，包括失败场景。

逐项判定依据见 `tests/expected/stage-1-validation.md`，自动化执行见 `tests/test_validate_analysis.py`。
