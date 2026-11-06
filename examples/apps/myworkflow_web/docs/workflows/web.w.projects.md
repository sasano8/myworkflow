# プロジェクトの一覧・作成・削除

固定ID：web.w.projects

[ワークフロー一覧](../workflows.md)

Webアプリの要件定義用カタログです。処理本体・画面・GitHub連携・開発環境の起動は未実装です。文書の生成は実行保証を意味しません。データの内部項目・制約と未決の設計案は入力資料で管理します。

## 処理・配置

### web.b.browse

処理：[web.p.browse](../shared-definitions.md#web.p.browse)

ステップ：[web.s.list_projects](../shared-definitions.md#web.s.list_projects)

ロール割当：system → [web.role.system](../shared-definitions.md#web.role.system)

- web.t.browse：一覧を開く／実行者：[web.role.user](../shared-definitions.md#web.role.user)
  入力元：[web.a.project_query](../shared-definitions.md#web.a.project_query) ← 一覧条件

### web.b.create

処理：[web.p.create](../shared-definitions.md#web.p.create)

ステップ：[web.s.create_project](../shared-definitions.md#web.s.create_project)

ロール割当：system → [web.role.system](../shared-definitions.md#web.role.system)

- web.t.create：プロジェクトを作成する／実行者：[web.role.user](../shared-definitions.md#web.role.user)
  入力元：[web.a.project_request](../shared-definitions.md#web.a.project_request) ← プロジェクト作成内容

### web.b.delete

処理：[web.p.delete](../shared-definitions.md#web.p.delete)

ステップ：[web.s.delete_project](../shared-definitions.md#web.s.delete_project)

ロール割当：system → [web.role.system](../shared-definitions.md#web.role.system)

- web.t.delete：プロジェクトを削除する／実行者：[web.role.user](../shared-definitions.md#web.role.user)
  入力元：[web.a.project](../shared-definitions.md#web.a.project) ← 対象プロジェクト


## ロール

- [web.role.user](../shared-definitions.md#web.role.user)：利用者
- [web.role.system](../shared-definitions.md#web.role.system)：システム

## 状態・遷移

未定義。

## 接続・待機

未定義。

## データ

- [web.a.project_query](../shared-definitions.md#web.a.project_query)：一覧条件
- [web.a.project_list](../shared-definitions.md#web.a.project_list)：プロジェクト一覧
- [web.a.project_request](../shared-definitions.md#web.a.project_request)：プロジェクト作成内容
- [web.a.project](../shared-definitions.md#web.a.project)：対象プロジェクト
- [web.a.deletion_result](../shared-definitions.md#web.a.deletion_result)：プロジェクト削除結果

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
