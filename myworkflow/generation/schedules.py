"""Schedule inventory from declarations, without registering any scheduler."""
from myworkflow._internal.markdown import escape
from myworkflow.contracts.schedules import validate_schedules


def render_schedules(schedules, catalog):
    validate_schedules(schedules, catalog)
    lines = ['# 定期実行一覧', '',
             '起動時刻は外部のcronが管理します。この文書の生成ではスケジュールを登録しません。', '',
             '[ワークフロー一覧](workflows.md)', '',
             '| スケジュールID | 名前 | cron式 | タイムゾーン | ワークフロー | 配置ID | トリガーID | 実行ロール |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for schedule in schedules:
        workflow = next(w for w in catalog.workflows if w.id == schedule.workflow_id)
        binding = next(b for b in workflow.bindings if b.id == schedule.binding_id)
        trigger = next(t for t in binding.triggers if t.id == schedule.trigger_id)
        role = next(r for r in catalog.roles if r.id == trigger.actor_role_id)
        cells = [escape(v) for v in (schedule.id, schedule.name, schedule.expression, schedule.timezone)]
        cells.extend([f'[{escape(workflow.name)}](workflows/{workflow.id}.md)', escape(binding.id), escape(trigger.id),
                      f'[{escape(role.display_name)}](shared-definitions.md#{role.id})'])
        lines.append('| ' + ' | '.join(cells) + ' |')
    if not schedules:
        lines.extend(['', '定期実行は未定義。'])
    lines.extend(['', 'cron式は数値によるUNIXの5項目（分・時・日・月・曜日）です。'
                  '`*`・列挙・範囲・間隔を使用でき、秒・年・名前付き曜日・マクロは対象外です。', ''])
    return '\n'.join(lines)
