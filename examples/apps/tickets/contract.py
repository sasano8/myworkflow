SPEC = {
    'roles': [
        {'id': 'role.system', 'name': 'チケット管理システム', 'display_name': 'システム'},
        {'id': 'ticket.operator', 'name': '窓口担当者', 'display_name': '受付担当'}],
    'artifacts': [
        {'id': 'ticket.number', 'name': '受付番号', 'key': 'number', 'type': 'str'},
        {'id': 'ticket.receipt', 'name': '発行結果', 'key': 'receipt', 'type': 'str'}],
    'pipelines': [{'id': 'ticket.issue', 'name': 'チケット発行', 'inputs': ['ticket.number'],
        'outputs': ['ticket.receipt'], 'reply': True, 'steps': [
            {'id': 'ticket.lock', 'name': '受付番号の排他', 'kind': 'lock', 'reads': ['ticket.number']},
            {'id': 'ticket.save', 'name': 'チケット保存', 'summary': '受付番号を重複なく登録し、発行結果を返す。',
             'kind': 'action', 'reads': ['ticket.number'], 'writes': ['ticket.receipt'],
             'uses': [['ticket.number', 'DB作成'], ['ticket.receipt', '保持']]}]}],
    'workflows': [{'id': 'ticket.workflow', 'name': '窓口でのチケット発行', 'bindings': [
        {'id': 'ticket.binding', 'pipeline': 'ticket.issue', 'triggers': [
            {'id': 'ticket.trigger', 'name': '担当者が発行を依頼', 'role': 'ticket.operator',
             'mapping': {'ticket.number': '受付番号'}}]}]}],
}
