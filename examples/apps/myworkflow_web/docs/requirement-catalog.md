# 要求カタログ

requirements.pyのアノテーションから生成する。コードを正本とし、この表は直接編集しない。

中心となる業務はプロジェクト詳細での開発。周辺機能と分けて表示する。参照の存在は検査するが、意味の充足・実装・受入テストの合格を保証しない。

## 中心：プロジェクト詳細での開発

| 要求ID | 名前 | 概要 | 対応先 |
| --- | --- | --- | --- |
| WEB-003 | プロジェクト詳細の表示 | 選択したプロジェクトの専用ページを表示する | web.screen.project、web.s.create_project |
| WEB-004 | 設定画面を開く | プロジェクトの設定画面を持つ | web.screen.settings、web.s.save_settings |
| WEB-005 | GitHub保存先の設定 | 保存先にGitHubを指定できる | web.screen.settings、web.s.save_settings |
| WEB-006 | 文書トップページの表示 | ドキュメントのトップページを表示する | web.screen.project、web.s.show_documents |
| WEB-007 | MkDocs文書の閲覧 | プロジェクトのMkDocsサイトをそのまま閲覧する体験を目指す。表示方式は未決 | web.screen.documents、web.s.show_documents |
| WEB-008 | 対話による要件入力 | 利用者が対話で要件を伝えられる | web.screen.chat、web.s.apply_requirements |
| WEB-009 | 要件のコード・文書反映 | 対話内容をコードへ反映し、対応するドキュメントを生成する | web.screen.chat、web.s.apply_requirements、web.s.build_preview |
| WEB-010 | 開発環境の自動準備 | Codespacesなどで開発環境を自動準備する。提供基盤は未決 | web.screen.chat、web.s.prepare_environment |
| WEB-011 | 手動ビルド | 手動ビルドボタンを持つ | web.screen.project、web.s.build_preview |
| WEB-012 | 要件反映後の自動ビルド | チャットによる要件反映後に自動ビルドできる | web.screen.build、web.s.build_preview |
| WEB-014 | 開発ガイド設定画面 | プロジェクトごとに開発ガイドを設定する画面を持つ | web.screen.guide、web.s.save_settings |
| WEB-015 | push先・ブランチ戦略の設定 | push先と作業ブランチの切り方の戦略を設定する。選択肢・既定値は未決 | web.screen.guide、web.s.save_settings |
| WEB-017 | コードを業務契約の正本にする | 業務契約はコードを正本とし、DBでは設定・会話・実行履歴を管理する。業務契約を二重管理しない | web.s.list_projects、web.s.apply_requirements |
| WEB-018 | 最後の成功版と版の差分を表示する | ビルド失敗時は最後の成功版を維持し、表示中のコミットと最新コードの版・差分を明示する。初回失敗なら未生成と表示する | web.s.build_preview、web.s.show_documents |
| WEB-019 | 自動プレビューと確定を分離する | 要件反映後に自動プレビューを作成する。ビルド成功だけを理由に保存・マージを確定しない | web.s.build_preview |
| WEB-020 | 会話から表示版まで追跡する | 会話からコード差分・検証結果・表示版を相互にたどれる | web.s.apply_requirements、web.s.build_preview、web.s.show_documents |

## 周辺機能

| 要求ID | 名前 | 概要 | 対応先 |
| --- | --- | --- | --- |
| WEB-001 | プロジェクト一覧の表示 | プロジェクト一覧を表示する | web.screen.projects、web.s.list_projects |
| WEB-002 | プロジェクト作成 | プロジェクトを作成できる | web.screen.projects、web.s.create_project |
| WEB-013 | プロジェクト削除 | プロジェクトを削除できる | web.screen.project、web.s.delete_project |
| WEB-016 | 開発ガイドテンプレートの管理 | プロジェクトの設定画面とは別に、開発ガイドテンプレートを管理する画面を持つ | web.screen.templates、web.s.manage_template |

[業務要件](requirements.md)・[画面一覧](screens.md)・[ワークフロー一覧](workflows.md)
