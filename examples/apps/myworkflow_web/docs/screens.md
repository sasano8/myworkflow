# 画面機能一覧

画面仕様のサンプルです。実際の画面や呼び出し処理は実装しません。

[ワークフロー一覧](workflows.md)／[共有定義](shared-definitions.md)

| 画面ID | 画面名 | 機能数 |
| --- | --- | --- |
| web.screen.projects | [プロジェクト一覧](#web.screen.projects) | 2 |
| web.screen.project | [プロジェクト詳細](#web.screen.project) | 4 |
| web.screen.settings | [プロジェクト設定](#web.screen.settings) | 2 |
| web.screen.guide | [開発ガイド設定](#web.screen.guide) | 2 |
| web.screen.templates | [開発ガイドテンプレート管理](#web.screen.templates) | 1 |
| web.screen.chat | [チャット](#web.screen.chat) | 3 |
| web.screen.documents | [ドキュメント](#web.screen.documents) | 1 |
| web.screen.build | [ビルド状況](#web.screen.build) | 1 |

<a id="web.screen.projects"></a>
## web.screen.projects：プロジェクト一覧

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WEB-001 | プロジェクト一覧の表示 | 一覧を開く | ワークフロー呼出 | プロジェクト一覧を表示する | [プロジェクトの一覧・作成・削除](workflows/web.w.projects.md) | web.b.browse | web.t.browse | [利用者](shared-definitions.md#web.role.user) |
| WEB-002 | プロジェクト作成 | 作成ボタンを押す | ワークフロー呼出 | プロジェクトを作成できる | [プロジェクトの一覧・作成・削除](workflows/web.w.projects.md) | web.b.create | web.t.create | [利用者](shared-definitions.md#web.role.user) |

<a id="web.screen.project"></a>
## web.screen.project：プロジェクト詳細

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WEB-003 | プロジェクト詳細の表示 | プロジェクトを選ぶ | ワークフロー呼出 | 選択したプロジェクトの専用ページを表示する | [プロジェクトの業務要件を確認する](workflows/web.w.documents.md) | web.b.review | web.t.review | [利用者](shared-definitions.md#web.role.user) |
| WEB-006 | 文書トップページの表示 | 文書トップを開く | ワークフロー呼出 | ドキュメントのトップページを表示する | [プロジェクトの業務要件を確認する](workflows/web.w.documents.md) | web.b.review | web.t.review | [利用者](shared-definitions.md#web.role.user) |
| WEB-011 | 手動ビルド | ビルドボタンを押す | ワークフロー呼出 | 手動ビルドボタンを持つ | [対話による要件反映と文書のビルド](workflows/web.w.development.md) | web.b.build | web.t.build | [利用者](shared-definitions.md#web.role.user) |
| WEB-013 | プロジェクト削除 | 削除操作を行う | ワークフロー呼出 | プロジェクトを削除できる | [プロジェクトの一覧・作成・削除](workflows/web.w.projects.md) | web.b.delete | web.t.delete | [利用者](shared-definitions.md#web.role.user) |

<a id="web.screen.settings"></a>
## web.screen.settings：プロジェクト設定

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WEB-004 | 設定画面を開く | 設定を開く | 画面単体 | プロジェクトの設定画面を持つ | — | — | — | — |
| WEB-005 | GitHub保存先の設定 | GitHub保存先を保存する | ワークフロー呼出 | 保存先にGitHubを指定できる | [GitHub接続と開発ガイドの設定](workflows/web.w.settings.md) | web.b.configure | web.t.configure | [利用者](shared-definitions.md#web.role.user) |

<a id="web.screen.guide"></a>
## web.screen.guide：開発ガイド設定

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WEB-014 | 開発ガイド設定画面 | 開発ガイドを開く | 画面単体 | プロジェクトごとに開発ガイドを設定する画面を持つ | — | — | — | — |
| WEB-015 | push先・ブランチ戦略の設定 | push先・ブランチ戦略を保存する | ワークフロー呼出 | push先と作業ブランチの切り方の戦略を設定する。選択肢・既定値は未決 | [GitHub接続と開発ガイドの設定](workflows/web.w.settings.md) | web.b.configure | web.t.configure | [利用者](shared-definitions.md#web.role.user) |

<a id="web.screen.templates"></a>
## web.screen.templates：開発ガイドテンプレート管理

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WEB-016 | 開発ガイドテンプレートの管理 | テンプレートを管理する | ワークフロー呼出 | プロジェクトの設定画面とは別に、開発ガイドテンプレートを管理する画面を持つ | [開発ガイドテンプレート管理](workflows/web.w.templates.md) | web.b.template | web.t.template | [利用者](shared-definitions.md#web.role.user) |

<a id="web.screen.chat"></a>
## web.screen.chat：チャット

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WEB-008 | 対話による要件入力 | 要件を送信する | ワークフロー呼出 | 利用者が対話で要件を伝えられる | [対話による要件反映と文書のビルド](workflows/web.w.development.md) | web.b.revise | web.t.revise | [利用者](shared-definitions.md#web.role.user) |
| WEB-009 | 要件のコード・文書反映 | 要件をコードへ反映する | ワークフロー呼出 | 対話内容をコードへ反映し、対応するドキュメントを生成する | [対話による要件反映と文書のビルド](workflows/web.w.development.md) | web.b.revise | web.t.revise | [利用者](shared-definitions.md#web.role.user) |
| WEB-010 | 開発環境の自動準備 | 開発環境の準備を依頼する | ワークフロー呼出 | Codespacesなどで開発環境を自動準備する。提供基盤は未決 | [対話による要件反映と文書のビルド](workflows/web.w.development.md) | web.b.revise | web.t.revise | [利用者](shared-definitions.md#web.role.user) |

<a id="web.screen.documents"></a>
## web.screen.documents：ドキュメント

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WEB-007 | MkDocs文書の閲覧 | 生成文書を閲覧する | ワークフロー呼出 | プロジェクトのMkDocsサイトをそのまま閲覧する体験を目指す。表示方式は未決 | [プロジェクトの業務要件を確認する](workflows/web.w.documents.md) | web.b.review | web.t.review | [利用者](shared-definitions.md#web.role.user) |

<a id="web.screen.build"></a>
## web.screen.build：ビルド状況

| 機能ID | 機能名 | 画面上の契機 | 種別 | 内容 | 呼び出すワークフロー | 配置ID | トリガーID | 呼び出すロール |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WEB-012 | 要件反映後の自動ビルド | 要件反映完了を受ける | ワークフロー呼出 | チャットによる要件反映後に自動ビルドできる | [対話による要件反映と文書のビルド](workflows/web.w.development.md) | web.b.build | web.t.auto_build | [システム](shared-definitions.md#web.role.system) |
