from myworkflow.markdown import escape


def render_quality(report):
    lines = ['# 業務要件の往復品質', '', f"ケース：{escape(report.get('case_id', '不明'))}。判定：{('基準内（既知の未表現あり）' if report.get('judgment') == 'meets-reviewed-baseline-with-known-gaps' else '基準内') if report['passed'] else '失敗'}。", '',
             '構造の一致は業務動作の保証ではありません。原文の意味評価は、レビューした要件単位と対応表の範囲です。', '',
             '| 指標 | 値 |', '| --- | --- |']
    labels = {'conversion_recall': '入力変換の再現率', 'conversion_precision': '入力変換の適合率',
              'roundtrip_recall': 'コード再出力の再現率', 'roundtrip_precision': 'コード再出力の適合率',
              'documented_coverage': '原文の記載充足率（要件単位）', 'structured_coverage': '原文の構造化率',
              'source_inventory_coverage': '原文の棚卸し範囲（非空白文字）'}
    for name, value in report.get('observed', {}).items():
        lines.append(f'| {escape(labels.get(name, name))} | {value:.2%} |')
    interfaces = report['metrics'].get('interfaces')
    if interfaces:
        lines += ['', '## 生成インターフェース', '',
                  f"{interfaces['expected_classes']}インターフェース中{interfaces['matched_classes']}インターフェースで項目・型・順序が一致。未実装の骨格の接続も検査し、業務処理そのものは実行しません。", '',
                  '| クラス | 期待する項目・型 | 実際 |', '| --- | --- | --- |']
        for error in interfaces['errors']:
            lines.append('| ' + ' | '.join(map(escape, (error['class'], error['expected'], error['actual']))) + ' |')
        for name in interfaces['unexpected_classes']:
            lines.append(f'| {escape(name)} | 定義なし | 余計なクラス |')
        if interfaces['passed']:
            lines.append('| 差分なし | — | — |')
    for name in ('conversion', 'roundtrip'):
        metric = report['metrics'].get(name)
        if metric:
            lines += ['', f'## {name} の差分', '', '| 種類 | 項目 | 期待値 | 実際 |', '| --- | --- | --- | --- |']
            for kind in ('missing', 'unexpected', 'mismatched'):
                for item in metric[kind]:
                    lines.append('| ' + ' | '.join(map(escape, (kind, item['path'], item.get('expected', '—'), item.get('actual', '—')))) + ' |')
            if metric['exact_match']:
                lines.append('| 差分なし | — | — | — |')
    source = report['metrics'].get('source')
    if source:
        lines += ['', '## 原文の表現状況', '',
                  f"全{source['total_units']}単位。構造化：{source['counts']['structured']}、概要文のみ：{source['counts']['description_only']}、欠損：{source['counts']['missing']}、未表現：{source['counts']['unrepresented']}。", '',
                  '| 要件ID | 判定 | 原文 | 補足 |', '| --- | --- | --- | --- |']
        for unit in source['units']:
            lines.append('| ' + ' | '.join(map(escape, (unit['id'], unit['status'], unit['quote'], unit['note']))) + ' |')
    if report['failures']:
        lines += ['', '## 失敗理由', ''] + ['- ' + escape(f) for f in report['failures']]
    lines += ['', '段階：' + '、'.join(f'{k}={v}' for k, v in report['stages'].items()), '']
    return '\n'.join(lines)
