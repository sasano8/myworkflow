# プロジェクトの業務要件を確認する

固定ID：web.w.documents

[ワークフロー一覧](../workflows.md)

Webアプリの要件定義用カタログです。処理本体・画面・GitHub連携・開発環境の起動は未実装です。文書の生成は実行保証を意味しません。データの内部項目・制約と未決の設計案は入力資料で管理します。

## 処理・配置

### web.b.review

処理：[web.p.review](../shared-definitions.md#web.p.review)

ステップ：[web.s.show_documents](../shared-definitions.md#web.s.show_documents)

ロール割当：system → [web.role.system](../shared-definitions.md#web.role.system)

- web.t.review：文書トップページを開く／実行者：[web.role.user](../shared-definitions.md#web.role.user)
  入力元：[web.a.project](../shared-definitions.md#web.a.project) ← 対象プロジェクト


## ロール

- [web.role.user](../shared-definitions.md#web.role.user)：利用者
- [web.role.system](../shared-definitions.md#web.role.system)：システム

## 状態・遷移

未定義。

## 接続・待機

未定義。

## データ

- [web.a.project](../shared-definitions.md#web.a.project)：対象プロジェクト
- [web.a.displayed_version](../shared-definitions.md#web.a.displayed_version)：最後の成功版と最新コードとの差分

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
