# GitHub接続と開発ガイドの設定

固定ID：web.w.settings

[ワークフロー一覧](../workflows.md)

Webアプリの要件定義用カタログです。処理本体・画面・GitHub連携・開発環境の起動は未実装です。文書の生成は実行保証を意味しません。データの内部項目・制約と未決の設計案は入力資料で管理します。

## 処理・配置

### web.b.configure

処理：[web.p.configure](../shared-definitions.md#web.p.configure)

ステップ：[web.s.save_settings](../shared-definitions.md#web.s.save_settings)

ロール割当：system → [web.role.system](../shared-definitions.md#web.role.system)

- web.t.configure：設定を保存する／実行者：[web.role.user](../shared-definitions.md#web.role.user)
  入力元：[web.a.project](../shared-definitions.md#web.a.project) ← 対象プロジェクト、[web.a.settings](../shared-definitions.md#web.a.settings) ← GitHub接続・開発ガイド設定


## ロール

- [web.role.user](../shared-definitions.md#web.role.user)：利用者
- [web.role.system](../shared-definitions.md#web.role.system)：システム

## 状態・遷移

未定義。

## 接続・待機

未定義。

## データ

- [web.a.project](../shared-definitions.md#web.a.project)：対象プロジェクト
- [web.a.settings](../shared-definitions.md#web.a.settings)：GitHub接続・開発ガイド設定

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
