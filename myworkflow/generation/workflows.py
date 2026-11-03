"""Workflow navigation over canonical declarations; shared definitions live once."""
from urllib.parse import quote

from myworkflow._internal.markdown import escape
from myworkflow.generation.documents import describe_step


def workflow_documents(catalog, *, graphs=(), cases=(), data_link=None, notice=None, schedules=()):
    catalog.validate()
    if schedules:
        from myworkflow.contracts.schedules import validate_schedules
        validate_schedules(schedules, catalog)
    if notice is None and catalog.id:
        notice = f"要求カタログ：{catalog.name}（{catalog.id}）。固定IDはこの要求カタログ内で解決します。"
    for graph in graphs:
        graph.validate(catalog)
    pipelines = {p.id: p for p in catalog.pipelines}
    graphs = {g.workflow.id: g for g in graphs}
    paths = {w.id: 'workflows/' + quote(w.id, safe='') + '.md' for w in catalog.workflows}
    names = {a.id: a.name for a in catalog.artifacts}
    shared = ['# 共有定義', '', '[ワークフロー一覧](workflows.md)', '']

    if notice:
        shared.extend([escape(notice), ""])

    def anchor(identity):
        return '<a id="' + quote(identity, safe='') + '"></a>'

    def reference(identity):
        return f'[{escape(identity)}](../shared-definitions.md#{quote(identity, safe="")})'

    def section(lines, title, values, *, empty="未定義。"):
        lines.extend(['## ' + title, ''])
        lines.extend(values or [empty])
        lines.append('')

    for role in catalog.roles:
        shared.extend([anchor(role.id), f'## {escape(role.id)}：{escape(role.name)}', '', escape(role.display_name), ''])
    for artifact in catalog.artifacts:
        shared.extend([anchor(artifact.id), f'## {escape(artifact.id)}：{escape(artifact.name)}', '',
                       f'キー：{escape(artifact.key)}／型：{escape(artifact.type)}', ''])
        if artifact.value_object:
            target = artifact.value_object.id
            shared.extend([f'データ制約：[{escape(target)}]({data_link}#{quote(target, safe="")})' if data_link else 'データ制約：未配置。', ''])
    for pipeline in catalog.pipelines:
        shared.extend([anchor(pipeline.id), f'## {escape(pipeline.id)}：{escape(pipeline.name)}', '',
                       '入力：' + ('、'.join(escape(i) for i in pipeline.inputs) or 'なし'), '',
                       '出力：' + ('、'.join(escape(i) for i in pipeline.outputs) or 'なし'), '',
                       '応答：' + ('あり' if pipeline.reply else 'なし'), ''])
        for step in pipeline.steps:
            summary = (f'排他キー：{", ".join(step.keys)}。範囲：{step.scope}。競合時：{step.conflict}。'
                       f'名前空間：{step.namespace}。最大待機：{step.timeout}秒。' if step.kind == 'lock'
                       else describe_step(step, names))
            shared.extend([anchor(step.id), f'### {escape(step.id)}：{escape(step.name)}', '', escape(summary), '',
                           f'実行ロール枠：{escape(step.actor)}', '',
                           '参照：' + ('、'.join(escape(i) for i in step.reads) or 'なし'), '',
                           '生成：' + ('、'.join(escape(i) for i in step.writes) or 'なし'), '',
                           '操作：' + ('、'.join(escape(u.operation + "：" + u.artifact_id) for u in step.uses) or 'なし'), ''])
    index = ['# ワークフロー一覧', '', '[共有定義](shared-definitions.md)', '', '| 固定ID | ワークフロー | 呼び出すロール | 配置数 |', '| --- | --- | --- | --- |']
    if notice:
        index[2:2] = [escape(notice), ""]
    result = {}
    placed = set()
    matched = set()
    for workflow in catalog.workflows:
        caller_ids = {t.actor_role_id for b in workflow.bindings for t in b.triggers}
        callers = '、'.join(
            f'[{escape(r.display_name)}](shared-definitions.md#{quote(r.id, safe="")})'
            for r in catalog.roles if r.id in caller_ids
        ) or '未定義'
        index.append(f'| {escape(workflow.id)} | [{escape(workflow.name)}]({paths[workflow.id]}) | {callers} | {len(workflow.bindings)} |')
        lines = [f'# {escape(workflow.name)}', '', f'固定ID：{escape(workflow.id)}', '', '[ワークフロー一覧](../workflows.md)', '']
        if notice:
            lines.extend([escape(notice), ""])
        related = {workflow.id}
        roles, artifacts, processing, connections = set(), set(), [], []
        for binding in workflow.bindings:
            pipeline = pipelines[binding.pipeline_id]
            related.update((binding.id, pipeline.id, *(s.id for s in pipeline.steps)))
            placed.add(pipeline.id)
            artifacts.update((*pipeline.inputs, *pipeline.outputs))
            for step in pipeline.steps:
                artifacts.update((*step.reads, *step.writes, *(u.artifact_id for u in step.uses)))
                if getattr(step, 'when', None):
                    artifacts.add(step.when[0])
            roles.update(r for _, r in binding.role_mapping)
            processing.extend([f'### {escape(binding.id)}', '', f'処理：{reference(pipeline.id)}', '',
                               'ステップ：' + (' → '.join(reference(s.id) for s in pipeline.steps) or '未定義'), '',
                               'ロール割当：' + ('、'.join(f'{escape(slot)} → {reference(r)}' for slot, r in binding.role_mapping) or '未定義'), ''])
            related.update(s.compensate for s in pipeline.steps if getattr(s, 'compensate', None))
            for trigger in binding.triggers:
                related.add(trigger.id)
                roles.add(trigger.actor_role_id)
                artifacts.update(a for a, _ in trigger.input_mapping)
                processing.extend([f'- {escape(trigger.id)}：{escape(trigger.name)}／実行者：{reference(trigger.actor_role_id)}',
                                   '  入力元：' + ('、'.join(f'{reference(a)} ← {escape(src)}' for a, src in trigger.input_mapping) or 'なし'), ''])
                if trigger.after or trigger.wait:
                    connections.append(f'- {escape(trigger.id)}：先行配置 {escape(trigger.after or "未定義")}／待機条件 {escape(trigger.wait or "未定義")}')
            if binding.next_workflow_id:
                target = binding.next_workflow_id
                connections.append(f'- {escape(binding.id)} → [{escape(target)}]({paths[target].split("/", 1)[1]})')
        for schedule in schedules:
            if schedule.workflow_id == workflow.id:
                related.add(schedule.id)
                connections.append(f'- 定期起動：{escape(schedule.id)}／cron：{escape(schedule.expression)}／'
                                   f'タイムゾーン：{escape(schedule.timezone)}／配置：{escape(schedule.binding_id)}／'
                                   f'トリガー：{escape(schedule.trigger_id)}（[定期実行一覧](../schedules.md)）')
        for other in catalog.workflows:
            for binding in other.bindings:
                if binding.next_workflow_id == workflow.id:
                    connections.append(f'- [{escape(other.id)}]({paths[other.id].split("/", 1)[1]})／{escape(binding.id)} → このワークフロー')
        related.update(roles | artifacts)
        placed.update(roles | artifacts)
        section(lines, '処理・配置', processing)
        section(lines, 'ロール', [f'- {reference(r.id)}：{escape(r.display_name)}' for r in catalog.roles if r.id in roles])
        graph = graphs.get(workflow.id)
        states = []
        if graph:
            related.update(s.id for s in (*graph.states, *graph.transitions))
            states = [f'初期状態：{escape(graph.initial.id)}', '']
            states += [f'- {escape(s.id)}：{escape(s.name)}' for s in graph.states]
            states += ['', '| 遷移 | 現在 | 成功後 | 配置・トリガー | 条件 |', '| --- | --- | --- | --- | --- |']
            for t in graph.transitions:
                guard = f'{t.guard.__module__}.{t.guard.__qualname__}' if t.guard else 'なし'
                states.append('| ' + ' | '.join(escape(v) for v in (t.id, t.source.id, t.target.id, t.binding.id + '/' + t.trigger.id, (t.condition or '未定義') + '／ガード：' + guard)) + ' |')
        section(lines, '状態・遷移', states)
        section(lines, '接続・待機', connections)
        section(lines, 'データ', [f'- {reference(a.id)}：{escape(a.name)}' for a in catalog.artifacts if a.id in artifacts])
        acceptance = []
        for case in cases:
            targets = set(case.requirements) & related
            if targets:
                matched.add(case.id)
                acceptance.append(f'- [{escape(case.name)}](../acceptance.md#{quote(case.id, safe="")})：' + '、'.join(escape(r) for r in case.requirements if r in targets))
        section(lines, '受入条件', acceptance)
        lines.extend(['宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。', ''])
        result[paths[workflow.id]] = '\n'.join(lines)
    index.append('')
    section(index, '未配置の共有定義', [f'- [{escape(e.id)}](shared-definitions.md#{quote(e.id, safe="")})：{escape(e.name)}'
            for e in (*catalog.pipelines, *catalog.roles, *catalog.artifacts) if e.id not in placed], empty="なし。")
    section(index, 'ワークフローに未対応の受入条件', [f'- [{escape(c.name)}](acceptance.md#{quote(c.id, safe="")})' for c in cases if c.id not in matched], empty="なし。")
    result['workflows.md'] = '\n'.join(index)
    result['shared-definitions.md'] = '\n'.join(shared)
    return result
