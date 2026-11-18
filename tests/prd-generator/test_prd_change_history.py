"""验证变更记录的窄屏概览、分版本明细和历史事件兼容。"""

from copy import deepcopy
import unittest

from prd_sync_support import load_script


def event(summary, *, kind='sync', version='0.5', time='2026-11-18T06:38:07.061375+00:00', ids=()):
    """构造事件样例；参数覆盖摘要、类型、版本、时间和编号，返回可渲染的事件，无预期异常。"""
    return {'time': time, 'prd_version': version, 'change_type': kind, 'summary': summary,
            'affected_prd_ids': list(ids), 'based_on_analysis_revision': 5, 'actor': 'prd_generator'}


class PrdChangeHistoryTests(unittest.TestCase):
    """核对按旧日志重新生成的 Markdown，不借展示去改写任何事件数据。"""

    def test_sync_summary_uses_reason_and_only_shows_changed_readiness(self):
        """短原因包含内部标点也完整保留，编号归类且不重复列出。"""
        reason = '确认 200 V 归高压；补充 199 V、200 V、201 V 的验收用例。'
        summary = ('新增：无；修改：PRD-AC-006、PRD-BR-006；废止：无；待确认：无；'
                   '就绪度：not_ready → ready_for_document；遗留事项：已按当前分析更新；分析事件说明：' + reason)
        events = [event(summary, ids=('PRD-AC-006', 'PRD-BR-006'))]
        before = deepcopy(events)
        text = load_script('render_info').render_changes(events)
        self.assertEqual(text.splitlines(), [
            '| 版本 / 时间 | 本次变更 |',
            '| --- | --- |',
            f'| **0.5**<br>2026-11-18 14:38:07 | {reason} 就绪度：未就绪 → 可生成文档。 |',
            '', '### 0.5 明细', '',
            '- **修改**：PRD-AC-006、PRD-BR-006',
            '- **遗留事项**：已按当前分析更新',
        ])
        self.assertEqual(events, before)

    def test_long_explanation_and_open_gaps_stay_in_details(self):
        """长原因和缺口依据完整保留，表内只显示确定的变化，不重复未变的就绪度。"""
        reason = '合成的完整说明；' * 20
        summary = ('新增：无；修改：无；废止：无；待确认：无；就绪度：not_ready → not_ready；遗留事项：未变；'
                   '核实关闭缺口：GAPREQ-1；保留缺口及占位（尚未提交经内容核实的关闭依据）：GAPREQ-2；'
                   '分析事件说明：' + reason)
        text = load_script('render_info').render_changes([event(summary)])
        overview, details = text.split('### 0.5 明细', 1)
        self.assertIn('| 同步分析：关闭 1 个缺口。 |', overview)
        self.assertNotIn(reason, overview)
        self.assertNotIn('就绪度', text)
        self.assertNotIn('遗留事项', text)
        self.assertIn('- **核实关闭缺口**：GAPREQ-1', details)
        self.assertIn('- **保留缺口及占位（尚未提交经内容核实的关闭依据）**：GAPREQ-2', details)
        self.assertIn(f'- **分析事件说明**：{reason}', details)

    def test_missing_reason_falls_back_to_actual_changes(self):
        """缺少原因时用真实数量概括；无条目变化时不杜撰业务改动，也不输出空明细。"""
        summary = '新增：无；修改：PRD-FR-001；废止：无；待确认：无；就绪度：not_ready → not_ready；遗留事项：未变'
        events = [event(summary, ids=('PRD-FR-001',), version='0.4'), event(summary.replace('修改：PRD-FR-001', '修改：无'))]
        text = load_script('render_info').render_changes(events)
        self.assertIn('| 同步至分析修订 5。 |', text)
        self.assertIn('| 同步分析：修改 1 项。 |', text)
        self.assertNotIn('### 0.5 明细', text)

    def test_freeform_legacy_entries_keep_text_and_same_version_events(self):
        """旧的非结构化同步说明不猜分类，竖线、换行和标记不能打断表格或文档结构。"""
        events = [event('旧版说明 | A&B\n<!-- /prd:section -->', ids=('PRD-FR-001',), time='2026-11-18 13:00:00'),
                  event('复核【与分析不一致】标注', kind='manual_edit_detected', ids=('PRD-AC-006',))]
        lines = load_script('render_info').render_changes(events).splitlines()
        self.assertEqual(lines[2:4], [
            '| **0.5**<br>2026-11-18 14:38:07 | 复核与分析不一致标注 |',
            '| **0.5**<br>2026-11-18 13:00:00 | 旧版说明 &#124; A&amp;B<br>&lt;!-- /prd:section --&gt; |',
        ])
        self.assertEqual(lines.count('### 0.5 明细'), 1)
        self.assertIn('**2026-11-18 14:38:07**\n\n- **受影响编号**：PRD-AC-006', '\n'.join(lines))
        self.assertIn('**2026-11-18 13:00:00**\n\n- **受影响编号**：PRD-FR-001', '\n'.join(lines))
