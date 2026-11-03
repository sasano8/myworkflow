"""Deterministic screen/feature inventory with workflow references."""
from urllib.parse import quote

from myworkflow._internal.markdown import escape
from myworkflow.contracts.screens import validate_screens


def render_screens(screens, catalog):
    validate_screens(screens, catalog)
    workflows = {w.id: w for w in catalog.workflows}
    roles = {r.id: r for r in catalog.roles}
    lines = ['# 画面機能一覧', '',
             '画面仕様のサンプルです。実際の画面や呼び出し処理は実装しません。', '',
             '[ワークフロー一覧](workflows.md)／[共有定義](shared-definitions.md)', '',
             '| 画面ID | 画面名 | 機能数 |', '| --- | --- | --- |']
    for screen in screens:
        lines.append(f'| {escape(screen.id)} | [{escape(screen.name)}](#{quote(screen.id, safe="")}) | {len(screen.features)} |')
    if not screens:
        lines.extend(['', '画面は未定義。'])
    for screen in screens:
        lines.extend(['', f'<a id="{quote(screen.id, safe="")}"></a>', f'## {escape(screen.id)}：{escape(screen.name)}', '',
                      '| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |',
                      '| --- | --- | --- | --- | --- | --- | --- | --- | --- |'])
        if not screen.features:
            lines.extend(['', '画面機能は未定義。'])
        for feature in screen.features:
            call = feature.workflow_call
            target, binding_id, trigger_id, caller = '—', '—', '—', '—'
            if call:
                workflow = workflows[call.workflow_id]
                binding = next(b for b in workflow.bindings if b.id == call.binding_id)
                trigger = next(t for t in binding.triggers if t.id == call.trigger_id)
                role = roles[trigger.actor_role_id]
                target = f'[{escape(workflow.name)}](workflows/{quote(workflow.id, safe="")}.md)'
                binding_id, trigger_id = escape(binding.id), escape(trigger.id)
                caller = f'[{escape(role.display_name)}](shared-definitions.md#{quote(role.id, safe="")})'
            cells = [escape(feature.id), escape(feature.name), escape(feature.event),
                     'ワークフロー呼出' if call else '画面単体', escape(feature.description),
                     target, binding_id, trigger_id, caller]
            lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines) + '\n'
