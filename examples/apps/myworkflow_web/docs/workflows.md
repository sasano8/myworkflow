# ワークフロー一覧

Webアプリの要件定義用カタログです。処理本体・画面・GitHub連携・開発環境の起動は未実装です。文書の生成は実行保証を意味しません。データの内部項目・制約と未決の設計案は入力資料で管理します。

[共有定義](shared-definitions.md)

| 固定ID | ワークフロー | 呼び出すロール | 配置数 |
| --- | --- | --- | --- |
| web.w.projects | [プロジェクトの一覧・作成・削除](workflows/web.w.projects.md) | [利用者](shared-definitions.md#web.role.user) | 3 |
| web.w.settings | [GitHub接続と開発ガイドの設定](workflows/web.w.settings.md) | [利用者](shared-definitions.md#web.role.user) | 1 |
| web.w.templates | [開発ガイドテンプレート管理](workflows/web.w.templates.md) | [利用者](shared-definitions.md#web.role.user) | 1 |
| web.w.development | [対話による要件反映と文書のビルド](workflows/web.w.development.md) | [利用者](shared-definitions.md#web.role.user)、[システム](shared-definitions.md#web.role.system) | 2 |
| web.w.documents | [プロジェクトの業務要件を確認する](workflows/web.w.documents.md) | [利用者](shared-definitions.md#web.role.user) | 1 |

## 未配置の共有定義

なし。

## ワークフローに未対応の受入条件

なし。
