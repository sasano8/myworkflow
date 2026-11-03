# サンプルと機能検証

## 業務アプリのサンプル

`apps/` は、フレームワークを使って開発する業務アプリの例。購買とチケット発行は、それぞれ独立したアプリである。

| ディレクトリ | 業務 | ドキュメント |
| --- | --- | --- |
| [apps/purchase](apps/purchase) | 申請から承認・発注確定まで（[画面機能一覧](apps/purchase/docs/screens.md)付き） | [docs](apps/purchase/docs/README.md) |
| [apps/tickets](apps/tickets) | チケット発行 | [docs](apps/tickets/docs/README.md) |

## 機能単位の技術検証

`feature_demos/` は、特定機能を小さいコードで検証する例。業務アプリ全体としての完成を示すものではない。

| ディレクトリ | 検証する機能 | ドキュメント |
| --- | --- | --- |
| [feature_demos/approval_values](feature_demos/approval_values) | データ定義・ガード・遷移と確定 | [docs](feature_demos/approval_values/docs/README.md) |
| [feature_demos/declarative_review](feature_demos/declarative_review) | 状態宣言・循環・図の出力 | [docs](feature_demos/declarative_review/docs/README.md) |
| [feature_demos/prepared_approval](feature_demos/prepared_approval) | アーティファクトの準備・確定・復旧 | [docs](feature_demos/prepared_approval/docs/README.md) |
| [feature_demos/manual_receipt](feature_demos/manual_receipt) | メール受信・申請書確認・台帳記入を人だけで行う業務の記述（自動実行なし） | [docs](feature_demos/manual_receipt/docs/README.md) |
| [feature_demos/product_catalogs](feature_demos/product_catalogs) | [銀行の概要](feature_demos/product_catalogs/docs/overview.md)から商品別の要求カタログへ進む | [docs](feature_demos/product_catalogs/docs/README.md) |

| [feature_demos/cron_reporting](feature_demos/cron_reporting) | cronによる日次実行・タイムゾーン・同じ対象日の再実行 | [docs](feature_demos/cron_reporting/docs/README.md) |

各例のdocsは `python -m scripts.generate_docs` またはpre-commit hookで生成する。実装する機能の保証範囲や残課題は、各生成物とリポジトリの設計文書で確認する。
