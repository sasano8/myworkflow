"""Root navigation and separate documents for each requirement catalog."""
from myworkflow._internal.markdown import escape
from myworkflow.generation.workflows import workflow_documents
from myworkflow.generation.data_definitions import render_data_definitions, data_definitions_source


def root_catalog_documents(root):
    root.validate()
    lines = [f'# {escape(root.name)}：要求カタログ一覧', '', f'ルートID：{escape(root.id)}', '',
             '各要求カタログが名前空間です。同じ固定IDを別の商品で使用できます。', '',
             '実行キューやデータ・権限の分離はこの一覧の管理範囲に含みません。', '',
             '| 要求カタログID | 名前 | ワークフロー数 |', '| --- | --- | --- |']
    result = {}
    for catalog in root.catalogs:
        directory = 'catalogs/' + catalog.id
        lines.append(f'| {escape(catalog.id)} | [{escape(catalog.name)}]({directory}/workflows.md) | {len(catalog.workflows)} |')
        notice = f'ルート：{root.name}（{root.id}）／要求カタログ：{catalog.name}（{catalog.id}）。固定IDはこの要求カタログ内で解決します。'
        data_link = 'data-definitions.md' if catalog.value_objects else None
        documents = workflow_documents(catalog, notice=notice, data_link=data_link)
        if catalog.value_objects:
            documents['data-definitions.md'] = render_data_definitions(catalog)
            documents['data-definitions.json'] = data_definitions_source(catalog)
        for path, text in documents.items():
            if path.endswith('.md'):
                text += '\n[要求カタログ一覧](' + ('../../../' if path.startswith('workflows/') else '../../') + 'catalogs.md)\n'
            result[directory + '/' + path] = text
    if not root.catalogs:
        lines.extend(['', '要求カタログは未定義。'])
    result['catalogs.md'] = '\n'.join(lines) + '\n'
    return result
