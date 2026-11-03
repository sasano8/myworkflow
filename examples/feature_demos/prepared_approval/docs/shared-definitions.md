# 共有定義

[ワークフロー一覧](workflows.md)

<a id="role.staged_system"></a>
## role.staged_system：業務システム

システム

<a id="role.staged_reviewer"></a>
## role.staged_reviewer：申請の審査責任者

承認者

<a id="a.staged_id"></a>
## a.staged_id：申請ID

キー：application_id／型：str

<a id="a.staged_version"></a>
## a.staged_version：申請バージョン

キー：application_version／型：int

<a id="a.staged_state_version"></a>
## a.staged_state_version：状態バージョン

キー：state_version／型：int

<a id="a.staged_changes"></a>
## a.staged_changes：確定予定の申請内容

キー：proposed／型：str

<a id="p.staged_approval"></a>
## p.staged_approval：申請の承認確定

入力：a.staged_id

出力：なし

応答：あり

<a id="s.staged_read"></a>
### s.staged_read：読込み・検証

申請と状態を読み、承認可能であることを確認する。

実行ロール枠：system

参照：a.staged_id

生成：a.staged_version、a.staged_state_version、a.staged_changes

操作：なし

<a id="s.staged_prepare"></a>
### s.staged_prepare：変更の準備

ジョブIDに申請と状態の変更を紐づけ、未確定で保存する。

実行ロール枠：system

参照：a.staged_id、a.staged_version、a.staged_state_version、a.staged_changes

生成：なし

操作：なし

<a id="s.staged_commit"></a>
### s.staged_commit：一括確定

バージョンの競合を検査し、申請と状態と確定結果をまとめて保存する。

実行ロール枠：system

参照：なし

生成：なし

操作：なし
