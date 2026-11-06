# 共有定義

[ワークフロー一覧](workflows.md)

Webアプリの要件定義用カタログです。処理本体・画面・GitHub連携・開発環境の起動は未実装です。文書の生成は実行保証を意味しません。データの内部項目・制約と未決の設計案は入力資料で管理します。

<a id="web.role.user"></a>
## web.role.user：プロジェクトの利用者

利用者

<a id="web.role.system"></a>
## web.role.system：myworkflow Webアプリ

システム

<a id="web.a.project_query"></a>
## web.a.project_query：一覧条件

キー：project_query／型：dict

<a id="web.a.project_list"></a>
## web.a.project_list：プロジェクト一覧

キー：project_list／型：dict

<a id="web.a.project_request"></a>
## web.a.project_request：プロジェクト作成内容

キー：project_request／型：dict

<a id="web.a.project"></a>
## web.a.project：対象プロジェクト

キー：project／型：dict

<a id="web.a.settings"></a>
## web.a.settings：GitHub接続・開発ガイド設定

キー：settings／型：dict

<a id="web.a.template"></a>
## web.a.template：開発ガイドテンプレート

キー：template／型：dict

<a id="web.a.chat_request"></a>
## web.a.chat_request：会話・要件変更依頼

キー：chat_request／型：dict

<a id="web.a.change_set"></a>
## web.a.change_set：会話と結び付いたコード差分

キー：change_set／型：dict

<a id="web.a.build_request"></a>
## web.a.build_request：ソース版を固定したビルド依頼

キー：build_request／型：dict

<a id="web.a.build_result"></a>
## web.a.build_result：ビルド・検証結果

キー：build_result／型：dict

<a id="web.a.displayed_version"></a>
## web.a.displayed_version：最後の成功版と最新コードとの差分

キー：displayed_version／型：dict

<a id="web.a.deletion_result"></a>
## web.a.deletion_result：プロジェクト削除結果

キー：deletion_result／型：dict

<a id="web.p.browse"></a>
## web.p.browse：プロジェクト一覧の取得

入力：web.a.project_query

出力：web.a.project_list

応答：あり

<a id="web.s.list_projects"></a>
### web.s.list_projects：一覧の取得

設定DBから利用者のプロジェクト一覧を取得する。業務契約の正本はコードとし、DBは運用情報だけを管理する。

実行ロール枠：system

参照：web.a.project_query

生成：web.a.project_list

操作：参照：web.a.project_query、保持：web.a.project_list

<a id="web.p.create"></a>
## web.p.create：プロジェクト作成

入力：web.a.project_request

出力：web.a.project

応答：あり

<a id="web.s.create_project"></a>
### web.s.create_project：プロジェクトの作成

プロジェクトを作成し、専用の詳細画面へ進めるようにする。

実行ロール枠：system

参照：web.a.project_request

生成：web.a.project

操作：参照：web.a.project_request、保持：web.a.project

<a id="web.p.delete"></a>
## web.p.delete：プロジェクト削除

入力：web.a.project

出力：web.a.deletion_result

応答：あり

<a id="web.s.delete_project"></a>
### web.s.delete_project：プロジェクトの削除

プロジェクトを削除する。進行中ジョブ・環境・保存データの整理と保持期間、GitHubリポジトリの扱いは未決とする。

実行ロール枠：system

参照：web.a.project

生成：web.a.deletion_result

操作：参照：web.a.project、保持：web.a.deletion_result

<a id="web.p.configure"></a>
## web.p.configure：プロジェクト設定・開発ガイドの保存

入力：web.a.project、web.a.settings

出力：web.a.settings

応答：あり

<a id="web.s.save_settings"></a>
### web.s.save_settings：GitHub接続と開発ガイドの設定

GitHub保存先とプロジェクトの開発ガイドを設定する。push先と作業ブランチの戦略を持つが、選択肢・既定値・PRやマージの方針は未決とする。

実行ロール枠：system

参照：web.a.project、web.a.settings

生成：web.a.settings

操作：参照：web.a.project、参照：web.a.settings

<a id="web.p.template"></a>
## web.p.template：開発ガイドテンプレート管理

入力：web.a.template

出力：web.a.template

応答：あり

<a id="web.s.manage_template"></a>
### web.s.manage_template：開発ガイドテンプレートの管理

プロジェクト設定とは独立した画面で共通の開発ガイドテンプレートを管理する。編集・適用・更新の伝播方法は未決とする。

実行ロール枠：system

参照：web.a.template

生成：web.a.template

操作：参照：web.a.template

<a id="web.p.revise"></a>
## web.p.revise：対話による要件反映

入力：web.a.chat_request

出力：web.a.change_set、web.a.build_request

応答：あり

<a id="web.s.prepare_environment"></a>
### web.s.prepare_environment：開発環境の準備

対象プロジェクトの開発環境を自動準備する。Codespacesなどの具体的な基盤は未決とする。

実行ロール枠：system

参照：web.a.chat_request

生成：なし

操作：参照：web.a.chat_request

<a id="web.s.apply_requirements"></a>
### web.s.apply_requirements：対話した要件をコードへ反映

会話を元にコードの業務契約を変更し、会話・基準版とコード差分を結び付ける。DBに業務契約の別正本を作らない。対象ソース版を特定した自動ビルド依頼を作る。

実行ロール枠：system

参照：web.a.chat_request

生成：web.a.change_set、web.a.build_request

操作：参照：web.a.chat_request、保持：web.a.change_set、保持：web.a.build_request

<a id="web.p.build"></a>
## web.p.build：文書のビルドとプレビュー

入力：web.a.build_request

出力：web.a.build_result

応答：あり

<a id="web.s.build_preview"></a>
### web.s.build_preview：文書生成・検証とプレビュー作成

固定したソース版から業務要件を生成・検証する。会話・コード差分・検証結果・表示版を追跡できるようにする。成功時にプレビューを更新し、失敗時は最後の成功版を維持する。初回失敗は未生成と表示する。ビルド成功を保存・マージの確定とはせず、開発ガイドの戦略を別途適用する。

実行ロール枠：system

参照：web.a.build_request

生成：web.a.build_result

操作：参照：web.a.build_request、保持：web.a.build_result

<a id="web.p.review"></a>
## web.p.review：プロジェクト文書の閲覧

入力：web.a.project

出力：web.a.displayed_version

応答：あり

<a id="web.s.show_documents"></a>
### web.s.show_documents：ドキュメントの閲覧

プロジェクトの文書トップページを表示する。表示中のコミットと最新コードとの差分、対応する会話・変更・検証結果を示す。MkDocsの表示・隔離方式は未決とする。

実行ロール枠：system

参照：web.a.project

生成：web.a.displayed_version

操作：参照：web.a.project、保持：web.a.displayed_version
