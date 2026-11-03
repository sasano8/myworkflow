# 画面機能一覧

画面仕様のサンプルです。実際の画面や呼び出し処理は実装しません。

[ワークフロー一覧](workflows.md)／[共有定義](shared-definitions.md)

| 画面ID | 画面名 | 機能数 |
| --- | --- | --- |
| screen.purchase_entry | [購買申請入力](#screen.purchase_entry) | 3 |
| screen.purchase_approval | [購買申請承認](#screen.purchase_approval) | 1 |
| screen.purchase_attachment | [見積書添付](#screen.purchase_attachment) | 2 |

<a id="screen.purchase_entry"></a>
## screen.purchase_entry：購買申請入力

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| feature.purchase_total | 合計金額の再計算 | 金額欄の値を変更する | 画面単体 | 入力値から合計金額を画面内で再計算して表示する。保存やワークフローの呼出は行わない。 | — | — | — | — |
| feature.purchase_reset | 入力のクリア | クリアボタンを押す | 画面単体 | 画面内の未送信の入力値を空に戻す。 | — | — | — | — |
| feature.purchase_submit | 購買申請の送信 | 申請ボタンを押す | ワークフロー呼出 | 入力した申請ID・取引先・金額を購買申請受付へ渡す。 | [購買申請の受付・承認](workflows/w.approval.md) | b.submit | t.submit | [申請者](shared-definitions.md#role.requester) |

<a id="screen.purchase_approval"></a>
## screen.purchase_approval：購買申請承認

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| feature.purchase_approve | 承認判断の送信 | 承認または却下を選び、実行ボタンを押す | ワークフロー呼出 | 対象の申請IDと承認判断を送信する。承認権限や本人確認は呼出先の契約に従う。 | [購買申請の受付・承認](workflows/w.approval.md) | b.approve | t.approve | [承認者](shared-definitions.md#role.approver) |

<a id="screen.purchase_attachment"></a>
## screen.purchase_attachment：見積書添付

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| feature.purchase_file_select | 添付ファイルの選択 | ファイル選択欄で見積書を選ぶ | 画面単体 | 選択したファイル名を画面内に表示する。この時点ではアップロードしない。 | — | — | — | — |
| feature.purchase_upload | 見積書2件の登録 | アップロードボタンを押す | ワークフロー呼出 | 申請IDと選択した見積書2件を見積書登録へ渡す。 | [購買申請への見積書添付](workflows/w.attach.md) | b.upload | t.upload | [申請者](shared-definitions.md#role.requester) |
