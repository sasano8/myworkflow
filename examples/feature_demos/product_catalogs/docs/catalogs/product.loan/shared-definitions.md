# 共有定義

[ワークフロー一覧](workflows.md)

ルート：サンプル銀行（org.example）／要求カタログ：融資商品（product.loan）。固定IDはこの要求カタログ内で解決します。

<a id="role.operator"></a>
## role.operator：商品運用部の業務担当者

業務担当者

<a id="role.system"></a>
## role.system：商品業務システム

システム

<a id="a.request"></a>
## a.request：融資申込

キー：request／型：str

<a id="p.process"></a>
## p.process：融資申込の処理

入力：a.request

出力：なし

応答：あり

<a id="s.check"></a>
### s.check：申込内容の確認

融資商品の申込内容と必要書類を確認する。

実行ロール枠：system

参照：a.request

生成：なし

操作：なし

<a id="s.calculate"></a>
### s.calculate：返済計画の計算

金利と返済期間を用いて返済計画を計算する。

実行ロール枠：system

参照：a.request

生成：なし

操作：なし

[要求カタログ一覧](../../catalogs.md)
