from myworkflow.acceptance.rendering import safe

def render_report(payload, cases, contract_hash, implementation_hash=None, *, options=None):
    from myworkflow.acceptance.rendering import DocumentOptions
    options = options or DocumentOptions()
    validate_report(payload)
    results = {r['case_id']: r for r in payload.get('cases', [])}
    known = {c.id for c in cases}
    if set(results) - known:
        raise ValueError('Report references unknown cases')
    statuses = {'passed': '合格', 'failed': '失敗', 'skipped': 'スキップ', 'not-run': '未実行'}
    lines = ['# ' + options.report_title, '',
             f"対象コミット：{safe(payload.get('commit') or '不明')}。未コミット変更：{safe(payload.get('working_tree_dirty'))}。",
             f"実行終了コード：{safe(payload.get('session_exitstatus'))}。", '',
             '定義が変わった結果は過去結果として表示します。仕様文書とは別の実行記録です。', '',
             '| ケースID | 業務契約 | 結果 |', '| --- | --- | --- |']
    for case in cases:
        result = results.get(case.id, {'status': 'not-run'})
        status = result['status']
        if status not in statuses:
            raise ValueError(f'Unknown result status: {status}')
        label = statuses[status]
        if status != 'not-run' and (result.get('source_sha256') != case.source_hash or result.get('contract_sha256', payload.get('contract_sha256')) != contract_hash or (implementation_hash is not None and result.get('implementation_sha256', payload.get('implementation_sha256')) != implementation_hash)):
            label = f'過去結果（定義変更あり）：{label}'
        lines.append(f'| {case.id} | {safe("、".join(case.requirements))} | {label} |')
    return '\n'.join(lines) + '\n'


def validate_report(payload):
    if not isinstance(payload, dict):
        raise ValueError('Report must be an object')
    if type(payload.get('schema_version')) is not int or payload.get('schema_version') != 1:
        raise ValueError('Unsupported or missing report schema_version')
    if type(payload.get('session_exitstatus')) is not int or not isinstance(payload.get('cases'), list):
        raise ValueError('Report requires an exit status and cases array')
    required = ('contract_sha256', 'implementation_sha256')
    if any(not isinstance(payload.get(key), str) for key in required):
        raise ValueError('Report requires contract and implementation fingerprints')
    seen = set()
    for case in payload['cases']:
        if not isinstance(case, dict):
            raise ValueError('Report case must be an object')
        identity = case.get('case_id')
        if not isinstance(identity, str) or identity in seen:
            raise ValueError('Report contains missing or duplicate case IDs')
        seen.add(identity)
        if case.get('status') not in {'passed', 'failed', 'skipped', 'not-run'}:
            raise ValueError(f'{identity}: invalid result status')
        if case['status'] != 'not-run' and not isinstance(case.get('source_sha256'), str):
            raise ValueError(f'{identity}: executed result requires a source fingerprint')
