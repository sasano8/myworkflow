# 購買の受入テスト

対象はフレームワークを使った購買アプリです。基盤の契約・実行・生成テストは別に残します。Gherkinを正本にした理由は、Scenario Outline・Examples、pytestのfixture・結果処理をそのまま利用できるためです。Python宣言との比較は[ツールのテスト](../tests/acceptance/test_acceptance.py)に残しています。

[正本のfeature](../examples/apps/purchase/acceptance/features/)から[受入仕様](../examples/apps/purchase/docs/acceptance.md)とpytest-bddの実行を得ます。業務契約とは固定IDで関連付け、文書は仕様、結果は別のJSON・Markdownとして扱います。

## 実行

[開発環境](../README.md#開発環境の構築)を準備して実行します。

```sh
python -m examples.apps.purchase.acceptance docs --check
python -m pytest tests/apps/purchase -q --acceptance-report artifacts/acceptance.json
python -m examples.apps.purchase.acceptance report artifacts/acceptance.json > artifacts/acceptance.md
# 必要なケースだけ選択する場合
python -m pytest tests/apps/purchase --acceptance-case scenario.purchase.schedule -q
```

Temporalの追加設定は[実行手順](temporal.md)に集約しています。文書更新は `docs`、書込みなしの検査は `docs --check` です。

## 判断と保証範囲

| 観点 | 確認方法・制約 |
| --- | --- |
| 操作と期待結果 | 業務Contextとは別のWorldからEngine.invokeを呼び、独立したSQL照会で検証 |
| 検証関数 | Thenは厳密にTrueを返す。空の検証を拒否し、誤った常時Trueはレビュー・変異試験で補う |
| ケース識別 | scenarioタグとOutlineのcase列で固定IDを作り、表示名・行順の変更後も追跡 |
| 定義検査 | 全featureの未知参照・曖昧操作・重複ID・期待結果不足を事前拒否。未対応のステップ内テーブル・docstringも拒否 |
| 日時 | 注入したローカル時計でJST／UTC、予定時刻の直前と到達を検査。タイムゾーン必須、逆戻り拒否 |
| Temporal | 実Worker・Signal・短い実時間Timer・子Workflowを使用。時間スキップ・絶対日時境界の検証ではない |
| 障害 | 差替え保存アダプターで応答消失・補償失敗・別所有者の保護を検査。実S3ではない |
| テストの検出力 | 早すぎる発注・重複発注・却下後発注・補償漏れの4変異を対象ケースで検出 |

待機は状態や結果を上限付きで確認し、固定sleepで準備完了を推測しません。ローカルスケジュールの永続化・クラッシュ復旧は対象外です。細かい条件とケース一覧は生成仕様を参照し、ここには転記しません。

## 結果の扱い

結果にはケース・契約ID、コミット、変更有無、feature・契約・実装／テスト基盤のハッシュ、ツールの版を記録します。passed・failed・skipped・not-runを区別し、未選択ケースを成功にしません。定義・実装のハッシュが違う成功は過去結果として表示し、失敗には診断を残します。形式はschema_version=1です。

期待結果を実装の出力から作り直しません。業務上の条件変更はAI・開発者がfeatureへ反映し、差分をレビューします。有限のケースですべてを保証せず、顧客レビュー・リモートCI確認と、本番環境の検証は[残課題](poc-plan.md)です。
