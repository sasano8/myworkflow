# 共有定義

[ワークフロー一覧](workflows.md)

<a id="role.guarded_system"></a>
## role.guarded_system：業務システム

システム

<a id="role.guarded_reviewer"></a>
## role.guarded_reviewer：審査責任者

承認者

<a id="a.guarded_id"></a>
## a.guarded_id：申請ID

キー：application_id／型：str

データ制約：[vo.application_id](data-definitions.md#vo.application_id)

<a id="p.guarded_approve"></a>
## p.guarded_approve：申請承認

入力：a.guarded_id

出力：なし

応答：あり

<a id="s.guarded_approve"></a>
### s.guarded_approve：承認変更の作成

申請者本人の承認を拒否し、承認者と承認済みの状態を変更予定に記録する。

実行ロール枠：system

参照：なし

生成：なし

操作：なし
