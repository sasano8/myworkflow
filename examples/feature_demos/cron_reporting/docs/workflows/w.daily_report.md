# 前日分の日次レポート作成

固定ID：w.daily_report

[ワークフロー一覧](../workflows.md)

要求カタログ：cronによる日次レポート（example.daily_report）。固定IDはこの要求カタログ内で解決します。

## 処理・配置

### b.daily_report

処理：[p.daily_report](../shared-definitions.md#p.daily_report)

ステップ：[s.create_report](../shared-definitions.md#s.create_report)

ロール割当：system → [role.report_system](../shared-definitions.md#role.report_system)

- t.daily_cron：cronの定期起動／実行者：[role.report_system](../shared-definitions.md#role.report_system)
  入力元：[a.report_date](../shared-definitions.md#a.report_date) ← business_date


## ロール

- [role.report_system](../shared-definitions.md#role.report_system)：システム

## 状態・遷移

未定義。

## 接続・待機

- 定期起動：cron.daily_report／cron：0 6 * * *／タイムゾーン：Asia/Tokyo／配置：b.daily_report／トリガー：t.daily_cron（[定期実行一覧](../schedules.md)）

## データ

- [a.report_date](../shared-definitions.md#a.report_date)：集計対象日
- [a.report](../shared-definitions.md#a.report)：日次レポート

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
