# 生成文書とpre-commit hook

## 有効化

[環境構築](../README.md#開発環境の構築)の `sh scripts/install-hooks.sh` をcloneごとに実行します。既存のhooksPath・実行可能hookは上書きせず停止します。その場合は既存hookから `python -m scripts.generate_docs --hook` を呼び出してください。

Pythonは `.venv/bin/python`、なければ `python3` を使用します。別環境は `MYWORKFLOW_PYTHON` で指定できます。生成にはacceptance依存が必要で、Temporalは不要です。

```sh
python -m scripts.generate_docs         # 更新のみ
python -m scripts.generate_docs --check # 書込みなしの差分検査
```

| コミット時の状態 | 動作 |
| --- | --- |
| 生成入力がすべてステージ済み | 再生成し、既知の生成物だけをステージ |
| 入力に未ステージ・未追跡の変更がある | 部分的な宣言の混入を避けるため停止 |
| 生成物に上書きされる未ステージ編集がある | 停止。確認後に明示的な生成を行う |
| 生成物が既に正しい | ステージ |
| 宣言検証・生成に失敗 | 停止 |

対象一覧は [scripts/generate_docs.py](../scripts/generate_docs.py) を正本とし、各カタログの `docs/` と購買の生成Requestを更新します。ソース・feature・無関係なファイルを自動ステージしません。原文・品質評価の入力・独立した期待値は自動更新しません。

CIも同じ `--check` を使います。出力一致は意味の正しさの証明ではなく、業務条件は独立した比較・受入テスト・レビューで確認します。ValueObjectの表示形式は[データ定義](value-objects.md)を参照してください。

## ワークフローから読む

各サンプルの `docs/README.md` から `workflows.md` の一覧、`workflows/<固定ID>.md` の詳細へ進みます。詳細は配置・トリガー、ロール、状態遷移、接続・待機、データ、受入条件を宣言順で集めます。共有処理・ステップ・ロール・データは `shared-definitions.md` に一度だけ生成し、各詳細から参照します。データ制約と受入シナリオの本文は既存文書へリンクします。

状態グラフや受入条件などがない項目は「未定義」、配置のない処理・ロール・データと未対応の受入条件は一覧末尾に表示します。関連付けは固定IDの一致で行い、文面から推測しません。状態遷移は成功後の宣言であり、実行履歴やテスト成功を示しません。従来の業務要件・受入文書も参照用に維持します。

ワークフロー一覧の「呼び出すロール」はサンプル宣言のトリガーにある `actor_role_id` から集め、ロールの表示名で共有定義へリンクします。重複はまとめてロール宣言順に表示し、自動起動のシステムも含めます。内部処理のロール割当は詳細ページで確認できます。トリガーがなければ「未定義」と表示します。

## 画面機能一覧

購買サンプルの [screens.py](../examples/apps/purchase/screens.py) は、画面ID・画面名の中に機能ID・機能名・画面上の契機・内容を定義します。`ScreenFeature.workflow_call` を省略すると画面単体の機能、`WorkflowCall` を指定すると既存ワークフローの配置・トリガーを呼び出す機能になります。例は金額変更時の再計算、クリアボタン、申請・承認・アップロードボタンです。

生成する [画面機能一覧](../examples/apps/purchase/docs/screens.md) は、呼出先のワークフロー詳細・呼び出すロールの共有定義へリンクします。ロールはトリガーから取得し、画面側で複製しません。画面・機能のID重複、空の操作契機、存在しないワークフロー、別ワークフローの配置や別配置のトリガーは生成前に検出します。画面仕様のみを記述するサンプルで、実際の画面・イベント処理や認可の実装は生成しません。

## 複数の要求カタログ

[商品別サンプル](../examples/feature_demos/product_catalogs/docs/catalogs.md) は、ルートカタログの配下に保険商品・融資商品の要求カタログを並べます。各 `ContractCatalog` 自体が名前空間で、別の名前空間クラスや入れ子のラッパーは設けません。

```python
insurance = ContractCatalog(..., id='product.insurance', name='保険商品')
loan = ContractCatalog(..., id='product.loan', name='融資商品')
root = RootCatalog('org.example', 'サンプル銀行', (insurance, loan))
workflow = root.workflow('product.insurance', 'w.main')
```

固定IDは要求カタログ内で一意です。両方に同じ `w.main`・`p.process` を定義できます。内部参照は従来どおりIDで解決し、外から選ぶときは要求カタログIDと定義IDを指定します。他の要求カタログへの暗黙の参照・検索はしません。組織共通のRole等は `shared.py` の同じ定義オブジェクトを参照します。

ルートは一覧と参照先をまとめ、子カタログを独立して検証します。子カタログのIDと名前は必須です。従来の単一カタログはID・名前を省略したまま利用できます。`compile_workflows` でも `catalog_id`・`catalog_name` を指定でき、互換specとビルドの業務IRは指定した識別情報を保持します。

生成文書は `catalogs.md` から `catalogs/<要求カタログID>/workflows.md` と専用詳細へ進みます。要求カタログは個別にProgram・Engineへ渡します。ルートは実行エンジンや永続化の境界ではなく、ワーカー・キュー・DB・権限による分離は別途設定します。

[銀行の概要](../examples/feature_demos/product_catalogs/docs/overview.md) は、ルートを銀行、子の要求カタログを商品とする例の入口です。対象業務・商品構成・共通担当・未定義の範囲を示し、各商品の詳細へリンクします。概要はサンプルの `root.py` から生成します。
