# 業務要件

Webアプリの要件定義用カタログです。処理本体・画面・GitHub連携・開発環境の起動は未実装です。文書の生成は実行保証を意味しません。データの内部項目・制約と未決の設計案は入力資料で管理します。

要求カタログ：myworkflow Webアプリ（myworkflow.web）

## ロール一覧

| ロールID | 業務上の正式名 | 表示名 |
| --- | --- | --- |
| web.role.user | プロジェクトの利用者 | 利用者 |
| web.role.system | myworkflow Webアプリ | システム |

## 001 プロジェクトの一覧・作成・削除

### 001-00001 プロジェクト一覧の取得

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001-00001-00000 | トリガー1：一覧を開く | 利用者 | 受付 | 入力元：一覧条件 ← 一覧条件 | 入力：一覧条件 | — | web.w.projects/web.b.browse/web.p.browse/request |
| 001-00001-00001 | — | システム | 一覧の取得 | 設定DBから利用者のプロジェクト一覧を取得する。業務契約の正本はコードとし、DBは運用情報だけを管理する。 | — | 参照：一覧条件／保持：プロジェクト一覧 | web.w.projects/web.b.browse/web.p.browse/web.s.list_projects |
| 001-00001-00002 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：プロジェクト一覧 | web.w.projects/web.b.browse/web.p.browse/response |

### 001-00002 プロジェクト作成

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001-00002-00000 | トリガー1：プロジェクトを作成する | 利用者 | 受付 | 入力元：プロジェクト作成内容 ← プロジェクト作成内容 | 入力：プロジェクト作成内容 | — | web.w.projects/web.b.create/web.p.create/request |
| 001-00002-00001 | — | システム | プロジェクトの作成 | プロジェクトを作成し、専用の詳細画面へ進めるようにする。 | — | 参照：プロジェクト作成内容／保持：対象プロジェクト | web.w.projects/web.b.create/web.p.create/web.s.create_project |
| 001-00002-00002 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：対象プロジェクト | web.w.projects/web.b.create/web.p.create/response |

### 001-00003 プロジェクト削除

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001-00003-00000 | トリガー1：プロジェクトを削除する | 利用者 | 受付 | 入力元：対象プロジェクト ← 対象プロジェクト | 入力：対象プロジェクト | — | web.w.projects/web.b.delete/web.p.delete/request |
| 001-00003-00001 | — | システム | プロジェクトの削除 | プロジェクトを削除する。進行中ジョブ・環境・保存データの整理と保持期間、GitHubリポジトリの扱いは未決とする。 | — | 参照：対象プロジェクト／保持：プロジェクト削除結果 | web.w.projects/web.b.delete/web.p.delete/web.s.delete_project |
| 001-00003-00002 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：プロジェクト削除結果 | web.w.projects/web.b.delete/web.p.delete/response |

## 002 GitHub接続と開発ガイドの設定

### 002-00001 プロジェクト設定・開発ガイドの保存

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 002-00001-00000 | トリガー1：設定を保存する | 利用者 | 受付 | 入力元：対象プロジェクト ← 対象プロジェクト、GitHub接続・開発ガイド設定 ← GitHub接続・開発ガイド設定 | 入力：対象プロジェクト、GitHub接続・開発ガイド設定 | — | web.w.settings/web.b.configure/web.p.configure/request |
| 002-00001-00001 | — | システム | GitHub接続と開発ガイドの設定 | GitHub保存先とプロジェクトの開発ガイドを設定する。push先と作業ブランチの戦略を持つが、選択肢・既定値・PRやマージの方針は未決とする。 | — | 参照：対象プロジェクト／参照：GitHub接続・開発ガイド設定 | web.w.settings/web.b.configure/web.p.configure/web.s.save_settings |
| 002-00001-00002 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：GitHub接続・開発ガイド設定 | web.w.settings/web.b.configure/web.p.configure/response |

## 003 開発ガイドテンプレート管理

### 003-00001 開発ガイドテンプレート管理

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 003-00001-00000 | トリガー1：テンプレートを管理する | 利用者 | 受付 | 入力元：開発ガイドテンプレート ← 開発ガイドテンプレート | 入力：開発ガイドテンプレート | — | web.w.templates/web.b.template/web.p.template/request |
| 003-00001-00001 | — | システム | 開発ガイドテンプレートの管理 | プロジェクト設定とは独立した画面で共通の開発ガイドテンプレートを管理する。編集・適用・更新の伝播方法は未決とする。 | — | 参照：開発ガイドテンプレート | web.w.templates/web.b.template/web.p.template/web.s.manage_template |
| 003-00001-00002 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：開発ガイドテンプレート | web.w.templates/web.b.template/web.p.template/response |

## 004 対話による要件反映と文書のビルド

### 004-00001 対話による要件反映

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 004-00001-00000 | トリガー1：要件をチャットで送信する | 利用者 | 受付 | 入力元：会話・要件変更依頼 ← 会話・要件変更依頼 | 入力：会話・要件変更依頼 | — | web.w.development/web.b.revise/web.p.revise/request |
| 004-00001-00001 | — | システム | 開発環境の準備 | 対象プロジェクトの開発環境を自動準備する。Codespacesなどの具体的な基盤は未決とする。 | — | 参照：会話・要件変更依頼 | web.w.development/web.b.revise/web.p.revise/web.s.prepare_environment |
| 004-00001-00002 | — | システム | 対話した要件をコードへ反映 | 会話を元にコードの業務契約を変更し、会話・基準版とコード差分を結び付ける。DBに業務契約の別正本を作らない。対象ソース版を特定した自動ビルド依頼を作る。 | — | 参照：会話・要件変更依頼／保持：会話と結び付いたコード差分／保持：ソース版を固定したビルド依頼 | web.w.development/web.b.revise/web.p.revise/web.s.apply_requirements |
| 004-00001-00003 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：会話と結び付いたコード差分、ソース版を固定したビルド依頼 | web.w.development/web.b.revise/web.p.revise/response |

### 004-00002 文書のビルドとプレビュー

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 004-00002-00000 | トリガー1：手動ビルドを実行する | 利用者 | 受付 | 入力元：ソース版を固定したビルド依頼 ← ソース版を固定したビルド依頼 | 入力：ソース版を固定したビルド依頼 | — | web.w.development/web.b.build/web.p.build/request |
| 004-00002-00000 | トリガー2：要件のコード反映が完了する | システム | 受付 | 先行配置：web.b.revise。入力元：ソース版を固定したビルド依頼 ← コード反映結果のビルド依頼 | 入力：ソース版を固定したビルド依頼 | — | web.w.development/web.b.build/web.p.build/request/web.t.auto_build |
| 004-00002-00001 | — | システム | 文書生成・検証とプレビュー作成 | 固定したソース版から業務要件を生成・検証する。会話・コード差分・検証結果・表示版を追跡できるようにする。成功時にプレビューを更新し、失敗時は最後の成功版を維持する。初回失敗は未生成と表示する。ビルド成功を保存・マージの確定とはせず、開発ガイドの戦略を別途適用する。 | — | 参照：ソース版を固定したビルド依頼／保持：ビルド・検証結果 | web.w.development/web.b.build/web.p.build/web.s.build_preview |
| 004-00002-00002 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：ビルド・検証結果 | web.w.development/web.b.build/web.p.build/response |

## 005 プロジェクトの業務要件を確認する

### 005-00001 プロジェクト文書の閲覧

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 005-00001-00000 | トリガー1：文書トップページを開く | 利用者 | 受付 | 入力元：対象プロジェクト ← 対象プロジェクト | 入力：対象プロジェクト | — | web.w.documents/web.b.review/web.p.review/request |
| 005-00001-00001 | — | システム | ドキュメントの閲覧 | プロジェクトの文書トップページを表示する。表示中のコミットと最新コードとの差分、対応する会話・変更・検証結果を示す。MkDocsの表示・隔離方式は未決とする。 | — | 参照：対象プロジェクト／保持：最後の成功版と最新コードとの差分 | web.w.documents/web.b.review/web.p.review/web.s.show_documents |
| 005-00001-00002 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：最後の成功版と最新コードとの差分 | web.w.documents/web.b.review/web.p.review/response |

## 型付き契約

| 固定ID | 名前 | コード上のキー | Python型 |
| --- | --- | --- | --- |
| web.a.project_query | 一覧条件 | project_query | dict |
| web.a.project_list | プロジェクト一覧 | project_list | dict |
| web.a.project_request | プロジェクト作成内容 | project_request | dict |
| web.a.project | 対象プロジェクト | project | dict |
| web.a.settings | GitHub接続・開発ガイド設定 | settings | dict |
| web.a.template | 開発ガイドテンプレート | template | dict |
| web.a.chat_request | 会話・要件変更依頼 | chat_request | dict |
| web.a.change_set | 会話と結び付いたコード差分 | change_set | dict |
| web.a.build_request | ソース版を固定したビルド依頼 | build_request | dict |
| web.a.build_result | ビルド・検証結果 | build_result | dict |
| web.a.displayed_version | 最後の成功版と最新コードとの差分 | displayed_version | dict |
| web.a.deletion_result | プロジェクト削除結果 | deletion_result | dict |

## 起動定義の対応

| トリガー固定ID | 配置 | パイプライン | 許可ロール |
| --- | --- | --- | --- |
| web.t.browse | web.b.browse | web.p.browse | web.role.user |
| web.t.create | web.b.create | web.p.create | web.role.user |
| web.t.delete | web.b.delete | web.p.delete | web.role.user |
| web.t.configure | web.b.configure | web.p.configure | web.role.user |
| web.t.template | web.b.template | web.p.template | web.role.user |
| web.t.revise | web.b.revise | web.p.revise | web.role.user |
| web.t.build | web.b.build | web.p.build | web.role.user |
| web.t.auto_build | web.b.build | web.p.build | web.role.system |
| web.t.review | web.b.review | web.p.review | web.role.user |
