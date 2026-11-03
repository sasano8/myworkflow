# 共有定義

[ワークフロー一覧](workflows.md)

要求カタログ：cronによる日次レポート（example.daily_report）。固定IDはこの要求カタログ内で解決します。

<a id="role.report_system"></a>
## role.report_system：日次レポート実行システム

システム

<a id="a.report_date"></a>
## a.report_date：集計対象日

キー：business_date／型：str

<a id="a.report"></a>
## a.report：日次レポート

キー：report／型：str

<a id="p.daily_report"></a>
## p.daily_report：日次レポート作成

入力：a.report_date

出力：a.report

応答：あり

<a id="s.create_report"></a>
### s.create_report：日次レポートの作成

対象日をキーに日次レポートを保存する。同じ対象日の再実行でもレポートを重複作成しない。

実行ロール枠：system

参照：a.report_date

生成：a.report

操作：なし
