"""Root navigation groups product catalogs without merging their definitions."""
from myworkflow import RootCatalog
from .insurance import CATALOG as insurance
from .loan import CATALOG as loan

ROOT = RootCatalog('org.example', 'サンプル銀行', (insurance, loan))

# Both resolve w.main, explicitly selecting the requirement catalog first.
insurance_workflow = ROOT.workflow('product.insurance', 'w.main')
loan_workflow = ROOT.workflow('product.loan', 'w.main')


def overview_document():
    """Bank-level entry document; product details remain in their own catalogs."""
    from myworkflow._internal.markdown import escape
    from .shared import operator, system

    ROOT.validate()
    lines = [f'# {escape(ROOT.name)}：業務要求の概要', '',
             '架空の銀行を例に、保険商品と融資商品の業務要求をまとめた入口です。', '',
             'このルートは銀行全体を表し、その配下の要求カタログが商品ごとの業務を表します。', '',
             '## 対象業務', '',
             '| 要求カタログ | 業務 | 主な処理 |', '| --- | --- | --- |']
    for catalog in ROOT.catalogs:
        work = '、'.join(escape(w.name) for w in catalog.workflows)
        steps = ' → '.join(escape(s.name) for p in catalog.pipelines for s in p.steps)
        lines.append(f'| [{escape(catalog.name)}](catalogs/{catalog.id}/workflows.md) | {work} | {steps} |')
    lines.extend(['', '## 銀行全体と商品の関係', '',
                  f'- ルートカタログ：{escape(ROOT.name)}。商品別の要求カタログを一覧にまとめます。',
                  '- 要求カタログ：保険商品・融資商品。ワークフロー、処理、データ、担当ロールを商品ごとに管理します。',
                  '- 商品内の詳細：ワークフロー一覧から専用詳細ページ、処理・ロール・データの共有定義へ進みます。', '',
                  '商品ごとに要求カタログを分けるため、同じワークフローIDでも別の業務を表せます。'
                  '保険商品の `w.main` は保険申込、融資商品の `w.main` は融資申込の業務です。', '',
                  '## 共通の担当', '',
                  f'- {escape(operator.display_name)}：{escape(operator.name)}。各商品の処理を依頼します。',
                  f'- {escape(system.display_name)}：{escape(system.name)}。商品内の各処理を担当します。', '',
                  'これらは銀行共通の[ロール定義](../shared.py)を商品別カタログから参照しています。', '',
                  '## このサンプルの範囲', '',
                  '保険申込の確認・保険料算定・審査資料作成と、融資申込の確認・返済計画計算を定義します。'
                  '実行ハンドラーや商品間の業務接続、受入条件は未定義です。'
                  '預金・振込・顧客管理など、銀行の他の業務はこのサンプルの対象に含めていません。', '',
                  '要求カタログは業務定義の整理単位です。実行負荷・データ・権限の分離は別途設計します。', '',
                  '## 詳細と定義', '',
                  '- [要求カタログ一覧](catalogs.md)',
                  '- [ルート定義](../root.py)',
                  '- 商品別定義：[保険](../insurance.py)／[融資](../loan.py)', ''])
    return '\n'.join(lines)
