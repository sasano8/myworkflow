# 業務要件

## ロール一覧

| ロールID | 業務上の正式名 | 表示名 |
| --- | --- | --- |
| role.system | チケット管理システム | システム |
| ticket.operator | 窓口担当者 | 受付担当 |

## 001 窓口でのチケット発行

### 001-00001 チケット発行

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001-00001-00000 | トリガー1：担当者が発行を依頼 | 受付担当 | 受付 | 入力元：受付番号 ← 受付番号 | 入力：受付番号 | — | ticket.workflow/ticket.binding/ticket.issue/request |
| 001-00001-00001 | — | システム | 受付番号の排他 | 排他キー：受付番号。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。 | — | 参照：受付番号／保持：排他キー・ロック | ticket.workflow/ticket.binding/ticket.issue/ticket.lock |
| 001-00001-00002 | — | システム | チケット保存 | 受付番号を重複なく登録し、発行結果を返す。 | — | DB作成：受付番号／保持：発行結果 | ticket.workflow/ticket.binding/ticket.issue/ticket.save |
| 001-00001-00003 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：発行結果 | ticket.workflow/ticket.binding/ticket.issue/response |

## 型付き契約

| 固定ID | 名前 | コード上のキー | Python型 |
| --- | --- | --- | --- |
| ticket.number | 受付番号 | number | str |
| ticket.receipt | 発行結果 | receipt | str |

## 起動定義の対応

| トリガー固定ID | 配置 | パイプライン | 許可ロール |
| --- | --- | --- | --- |
| ticket.trigger | ticket.binding | ticket.issue | ticket.operator |

## 実装対応

| 固定ID | 実装 |
| --- | --- |
| ticket.save | examples.apps.tickets.application.issue |

ロックはEngine → LockProvider、受付認可はEngine → Principal.rolesで実行。詳細は[実行設計](../../../../docs/architecture.md)を参照。

## 受入条件との対応

<a id="ticket.issue"></a>
### ticket.issue

- [受付担当がチケットを発行する](acceptance.md#scenario.tickets.issue)
