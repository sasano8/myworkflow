# 業務要件

## ロール一覧

| ロールID | 業務上の正式名 | 表示名 |
| --- | --- | --- |
| role.requester | 購買依頼部門の担当者 | 申請者 |
| role.approver | 購買依頼部門の部門長 | 承認者 |
| role.buyer | 購買部の発注担当者 | 発注担当者 |
| role.system | 購買管理システム | システム |

## 001 購買申請の受付・承認

### 001-00001 購買申請受付

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001-00001-00000 | トリガー1：申請者がFEで申請 | 申請者 | 受付 | 入力元：購買申請ID ← id、取引先 ← vendor、申請金額 ← amount | 入力：購買申請ID、取引先、申請金額 | — | w.approval/b.submit/p.submit/request |
| 001-00001-00001 | — | システム | 申請単位の排他 | 排他キー：購買申請ID。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。 | — | 参照：購買申請ID／保持：排他キー・ロック | w.approval/b.submit/p.submit/s.submit-lock |
| 001-00001-00002 | — | システム | 申請保存 | 正の金額と取引先を確認し、申請者に紐づく承認待ちの申請を保存する。 | — | DB作成：購買申請ID／保持：申請状態 | w.approval/b.submit/p.submit/s.submit |
| 001-00001-00003 | — | システム | 結果返却 | 結果を返す。 | 出力：購買申請ID、申請状態 | — | w.approval/b.submit/p.submit/response |

### 001-00002 承認判断の反映

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001-00002-00000 | トリガー1：承認者がFEで承認または却下 | 承認者 | 受付 | 待機・再開条件：承認イベントを受信。入力元：購買申請ID ← id、承認判断 ← decision | 入力：購買申請ID、承認判断 | — | w.approval/b.approve/p.approve/request |
| 001-00002-00001 | — | システム | 申請単位の排他 | 排他キー：購買申請ID。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。 | — | 参照：購買申請ID／保持：排他キー・ロック | w.approval/b.approve/p.approve/s.approve-lock |
| 001-00002-00002 | — | システム | 承認対象確認 | 承認待ちかつ申請者と承認者が別人であることを確認する。 | — | — | w.approval/b.approve/p.approve/s.check-approval |
| 001-00002-00003 | — | システム | 承認 | 承認済みに更新する。 条件：承認判断がTrueの場合。その他はスキップし次へ合流。 | — | DB更新：申請状態 | w.approval/b.approve/p.approve/s.approve |
| 001-00002-00004 | — | システム | 却下 | 却下済みに更新する。発注は行わない。 条件：承認判断がFalseの場合。その他はスキップし次へ合流。 | — | DB更新：申請状態 | w.approval/b.approve/p.approve/s.reject |
| 001-00002-00005 | — | システム | 結果返却 | 結果を返す。 | 出力：申請状態 | — | w.approval/b.approve/p.approve/response |

### 001-00003 発注確定の起動

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001-00003-00000 | トリガー1：指定日時に到達 | システム | 受付 | 待機・再開条件：承認済みかつ指定日時に到達。入力元：購買申請ID ← id | 入力：購買申請ID | — | w.approval/b.dispatch/p.dispatch/request |
| 001-00003-00000 | トリガー2：発注担当者がFEで開始 | 発注担当者 | 受付 | 入力元：購買申請ID ← application | 入力：購買申請ID | — | w.approval/b.dispatch/p.dispatch/request/t.manual |
| 001-00003-00001 | — | システム | 引継ぎ条件確認 | 承認済みの購買申請IDを次ワークフローへ引き継ぐ。 | — | — | w.approval/b.dispatch/p.dispatch/s.dispatch |
| 001-00003-00002 | — | システム | 結果返却 | 結果を返す。次ワークフロー起動：承認済み購買申請の発注確定。 | 出力：購買申請ID | — | w.approval/b.dispatch/p.dispatch/response |

## 002 購買申請への見積書添付

### 002-00001 見積書2件登録

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 002-00001-00000 | トリガー1：申請者が見積書2件をアップロード | 申請者 | 受付 | 入力元：購買申請ID ← id、見積書A ← file_a、見積書B ← file_b | 入力：購買申請ID、見積書A、見積書B | — | w.attach/b.upload/p.upload/request |
| 002-00001-00001 | — | システム | 申請単位の排他 | 排他キー：購買申請ID。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。 | — | 参照：購買申請ID／保持：排他キー・ロック | w.attach/b.upload/p.upload/s.upload-lock |
| 002-00001-00002 | — | システム | 添付可否確認 | 申請者本人であり、申請が承認待ちであることを確認する。 | — | — | w.attach/b.upload/p.upload/s.check-upload |
| 002-00001-00003 | — | システム | 見積書A保存 | 今回の実行専用キーで見積書Aを保存する。 失敗時の補償：c.delete-a（逆順、失敗した処理も対象）。 一時障害のみ最大2回試行。 | — | 参照：見積書A | w.attach/b.upload/p.upload/s.put-a |
| 002-00001-00004 | — | システム | 見積書B保存 | 見積書Bを保存し、両方の添付情報を申請に紐づける。 失敗時の補償：c.delete-b（逆順、失敗した処理も対象）。 一時障害のみ最大2回試行。 | — | 参照：見積書B／DB作成：添付登録結果 | w.attach/b.upload/p.upload/s.put-b |
| 002-00001-00005 | — | システム | 結果返却 | 結果を返す。 | 出力：添付登録結果 | — | w.attach/b.upload/p.upload/response |

## 003 承認済み購買申請の発注確定

### 003-00001 発注確定

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 003-00001-00000 | トリガー1：承認ワークフローから起動 | システム | 受付 | 入力元：購買申請ID ← id | 入力：購買申請ID | — | w.execution/b.confirm/p.confirm/request |
| 003-00001-00001 | — | システム | 申請単位の排他 | 排他キー：購買申請ID。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。 | — | 参照：購買申請ID／保持：排他キー・ロック | w.execution/b.confirm/p.confirm/s.order-lock |
| 003-00001-00002 | — | システム | 発注条件照会 | 承認済み、見積書2件あり、未発注であることを確認する。 | — | 保持：発注可能 | w.execution/b.confirm/p.confirm/s.eligibility |
| 003-00001-00003 | — | システム | 発注確定 | 発注作成と申請の発注確定済みへの更新を同一DBトランザクションで行う。 条件：発注可能がTrueの場合。その他はスキップし次へ合流。 | — | DB作成：発注番号／DB更新：申請状態 | w.execution/b.confirm/p.confirm/s.confirm |
| 003-00001-00004 | — | システム | 発注拒否 | 発注条件を満たさなければエラーとして終了し、発注しない。 条件：発注可能がFalseの場合。その他はスキップし次へ合流。 | — | — | w.execution/b.confirm/p.confirm/s.stop |
| 003-00001-00005 | — | システム | 完了 | 処理を完了する。応答は返さない。 | 出力：なし（応答不要） | — | w.execution/b.confirm/p.confirm/response |

## 型付き契約

| 固定ID | 名前 | コード上のキー | Python型 |
| --- | --- | --- | --- |
| a.id | 購買申請ID | application_id | str |
| a.vendor | 取引先 | vendor | str |
| a.amount | 申請金額 | amount | int |
| a.status | 申請状態 | status | str |
| a.quote-a | 見積書A | quote_a | str |
| a.quote-b | 見積書B | quote_b | str |
| a.receipt | 添付登録結果 | receipt | str |
| a.decision | 承認判断 | decision | bool |
| a.eligible | 発注可能 | eligible | bool |
| a.order | 発注番号 | order_id | str |

## 起動定義の対応

| トリガー固定ID | 配置 | パイプライン | 許可ロール |
| --- | --- | --- | --- |
| t.submit | b.submit | p.submit | role.requester |
| t.approve | b.approve | p.approve | role.approver |
| t.timer | b.dispatch | p.dispatch | role.system |
| t.manual | b.dispatch | p.dispatch | role.buyer |
| t.upload | b.upload | p.upload | role.requester |
| t.confirm | b.confirm | p.confirm | role.system |

## 実装対応

| 固定ID | 実装 |
| --- | --- |
| c.delete-a | examples.purchase.handlers.delete_a |
| c.delete-b | examples.purchase.handlers.delete_b |
| s.approve | examples.purchase.handlers.approve |
| s.check-approval | examples.purchase.handlers.check_approval |
| s.check-upload | examples.purchase.handlers.check_upload |
| s.confirm | examples.purchase.handlers.confirm |
| s.dispatch | examples.purchase.handlers.dispatch |
| s.eligibility | examples.purchase.handlers.eligibility |
| s.put-a | examples.purchase.handlers.put_a |
| s.put-b | examples.purchase.handlers.put_b |
| s.reject | examples.purchase.handlers.reject |
| s.stop | examples.purchase.handlers.stop |
| s.submit | examples.purchase.handlers.submit |

ロックはEngine → LockProvider、受付認可はEngine → Principal.rolesで実行。詳細は[実行設計](../../docs/execution-design.md)を参照。
