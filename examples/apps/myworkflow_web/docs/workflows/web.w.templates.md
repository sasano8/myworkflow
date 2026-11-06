# 開発ガイドテンプレート管理

固定ID：web.w.templates

[ワークフロー一覧](../workflows.md)

Webアプリの要件定義用カタログです。処理本体・画面・GitHub連携・開発環境の起動は未実装です。文書の生成は実行保証を意味しません。データの内部項目・制約と未決の設計案は入力資料で管理します。

## 処理・配置

### web.b.template

処理：[web.p.template](../shared-definitions.md#web.p.template)

ステップ：[web.s.manage_template](../shared-definitions.md#web.s.manage_template)

ロール割当：system → [web.role.system](../shared-definitions.md#web.role.system)

- web.t.template：テンプレートを管理する／実行者：[web.role.user](../shared-definitions.md#web.role.user)
  入力元：[web.a.template](../shared-definitions.md#web.a.template) ← 開発ガイドテンプレート


## ロール

- [web.role.user](../shared-definitions.md#web.role.user)：利用者
- [web.role.system](../shared-definitions.md#web.role.system)：システム

## 状態・遷移

未定義。

## 接続・待機

未定義。

## データ

- [web.a.template](../shared-definitions.md#web.a.template)：開発ガイドテンプレート

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
