# 対話による要件反映と文書のビルド

固定ID：web.w.development

[ワークフロー一覧](../workflows.md)

Webアプリの要件定義用カタログです。処理本体・画面・GitHub連携・開発環境の起動は未実装です。文書の生成は実行保証を意味しません。データの内部項目・制約と未決の設計案は入力資料で管理します。

## 処理・配置

### web.b.revise

処理：[web.p.revise](../shared-definitions.md#web.p.revise)

ステップ：[web.s.prepare_environment](../shared-definitions.md#web.s.prepare_environment) → [web.s.apply_requirements](../shared-definitions.md#web.s.apply_requirements)

ロール割当：system → [web.role.system](../shared-definitions.md#web.role.system)

- web.t.revise：要件をチャットで送信する／実行者：[web.role.user](../shared-definitions.md#web.role.user)
  入力元：[web.a.chat_request](../shared-definitions.md#web.a.chat_request) ← 会話・要件変更依頼

### web.b.build

処理：[web.p.build](../shared-definitions.md#web.p.build)

ステップ：[web.s.build_preview](../shared-definitions.md#web.s.build_preview)

ロール割当：system → [web.role.system](../shared-definitions.md#web.role.system)

- web.t.build：手動ビルドを実行する／実行者：[web.role.user](../shared-definitions.md#web.role.user)
  入力元：[web.a.build_request](../shared-definitions.md#web.a.build_request) ← ソース版を固定したビルド依頼

- web.t.auto_build：要件のコード反映が完了する／実行者：[web.role.system](../shared-definitions.md#web.role.system)
  入力元：[web.a.build_request](../shared-definitions.md#web.a.build_request) ← コード反映結果のビルド依頼


## ロール

- [web.role.user](../shared-definitions.md#web.role.user)：利用者
- [web.role.system](../shared-definitions.md#web.role.system)：システム

## 状態・遷移

未定義。

## 接続・待機

- web.t.auto_build：先行配置 web.b.revise／待機条件 未定義

## データ

- [web.a.chat_request](../shared-definitions.md#web.a.chat_request)：会話・要件変更依頼
- [web.a.change_set](../shared-definitions.md#web.a.change_set)：会話と結び付いたコード差分
- [web.a.build_request](../shared-definitions.md#web.a.build_request)：ソース版を固定したビルド依頼
- [web.a.build_result](../shared-definitions.md#web.a.build_result)：ビルド・検証結果

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
