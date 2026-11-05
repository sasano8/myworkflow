# トランジション契約と変更の一括確定

## 使い方

[承認サンプル](../examples/feature_demos/approval_values/application.py)では、クラス宣言の状態・遷移と `TransitionRuntime` を同じEngineへ接続する。

```python
from myworkflow.runtime.transitions import TransitionRuntime

transitions = TransitionRuntime(
    compiled,
    compiled.graphs[0],
    coordinator,
    key=lambda values: f"application:{values['application_id']}",
    state_field="status",
)
# Engine(..., transitions=transitions)
```

`key` はマッピング・型検査済みのパイプライン入力から対象レコードを特定する。対象は既存のJSONオブジェクトで、`status` に宣言された状態の固定IDを保存する。別の項目名なら `state_field` で指定する。初期レコードの作成や、状態が別キーに保存されている既存データの変換は自動で行わない。

ハンドラーは通常の項目更新を預けるだけでよい。

```python
application = ctx.changes.subject
ctx.changes.update(
    application,
    approved_by=ctx.actor,
    status=Approval.approved.id,
)
```

`subject` は検証対象の申請を読み込んだRecordである。`record.value` は読込み時の値のコピー、`record.version` はそのバージョン。`ctx.changes.read(key)` で他の既存JSONレコードを読み、`update(record, **fields)` でそれらの項目も変更できる。同じキーは同じ読込み結果を返し、変更予定を公開したり最新値へ更新したりしない。変更内容は内部にコピーし、別のChangesで読んだRecordの更新や、実行終了後の更新は拒否する。

[ValueObject](value-objects.md)を `TransitionRuntime(..., value_object=definition)` へ結び付けると、対象レコードを読込時と確定前に検証する。他のレコードも `ctx.changes.read(key, value_object=definition)` で型を指定できる。型検証後の状態をトランジションと照合する。

新規レコード作成・削除・blobのステージはこの高水準APIの対象外である。既存の低水準Coordinator APIは引き続き使用できるが、低水準APIを直接呼ぶ書込みにこの検証が自動適用されるわけではない。

## 宣言する条件

自然言語の `condition` は業務概要、`guard` は実行する純粋なPython関数である。

```python
def may_approve(ctx):
    return ctx.application["owner"] != ctx.actor and ctx.application["amount"] > 0


# ワークフローのクラス内
approve = transition(
    "tr.approve",
    "承認",
    waiting,
    approved,
    execute,
    requested,
    condition="申請者本人ではなく、金額が正である",
    guard=may_approve,
)
```

ガードには `GuardContext(actor, application, inputs)` を渡す。申請と入力は開始時点のコピーであり、ガード内で変更しても保存されない。戻り値は厳密にboolとする。副作用や時間依存の判断を持たせない。宣言に条件文があるのにガードが接続されていない場合、実行アダプターの構築を拒否する。自然言語と関数の意味が一致すること自体は、レビュー・受入テストで確認する。

ガード関数はクラス宣言から状態グラフへ参照を引き継ぎ、IRには関数名も出力する。ガードのimportや実行計画の復元をIRから自動で行う機能ではない。

## 実行と保存の順序

1. `Engine.invoke` がトリガーのロール・入力を検証する。利用者本人の認証とPrincipalの作成は呼出し側が担う。
2. 対象の申請とバージョンを読み、配置・トリガー・現在の状態に合う遷移のガードを評価する。
3. 適格な遷移がちょうど一つならパイプラインを実行する。ゼロ件・複数件は拒否し、宣言順で選ばない。
4. 全ステップと出力検査が成功した後、変更予定の申請の状態が、その遷移の成功後の状態と一致するか検証する。変更なしや不一致なら確定しない。
5. Engineが変更全体をprepareし、読込み時のバージョンでcommitする。申請の業務項目と状態、他の更新対象、確定結果を同じCoordinatorの保存境界で反映する。
6. 排他ロックを解放し、実行履歴を成功として記録する。

ハンドラーから明示的にprepare・commitする必要はない。ガードの判断に使った申請が処理途中で更新されても、最後のバージョン照合で変更全体を拒否する。対象パイプラインへの `run`・`run_internal`・`run_or_raise` は、このアダプターを接続したEngineでは拒否する。ロールとトリガーを検証する `invoke` または `invoke_or_raise` を使用する。

## 失敗と復旧

| 失敗箇所 | 扱い |
| --- | --- |
| ロール・開始状態・ガード・遷移選択 | ハンドラーを実行せず拒否 |
| ハンドラー・成功後の状態検査 | 変更予定を確定しない。既存の補償処理があれば実行 |
| 楽観ロックの競合 | 変更全体を確定しない。準備は残るため照会・破棄し、再判断には新しいジョブIDを使う |
| prepare試行後の停止・commit応答消失 | 結果照会が必要な復旧対象とし、自動補償を控える |
| commit成功後のロック解放・履歴保存失敗 | 確定済みデータを自動補償せず、復旧対象として記録を試みる |

prepareの応答消失でも準備が残っている可能性があるため、試行開始後は保守的に復旧対象とする。Engineは可能なら `manual-recovery` を記録し、終了結果にcriticalメッセージを加える。履歴ストア自身が故障していれば、その記録成功までは保証できない。ジョブIDは `Context.run_id` とし、Coordinatorの `status(run_id)` を正として照会する。検証済みの準備は別プロセスから同じIDで確定できるが、ジョブの内容や業務判断を変更して再利用してはいけない。

## 保証の範囲と残課題

一つの明示的な状態グラフを、既存JSONレコードの一つの状態フィールドへ接続する仕組みである。アダプターはそのグラフの配置に適用する。状態グラフ単体や、アダプターを接続していないEngineが自動で契約を強制するものではない。

楽観ロックで検査するのは書込み対象であり、読んだだけの別レコードや、ガードのクロージャが参照する外部情報まで検査しない。ハンドラーやProviderは信頼されたアプリケーションコードであり、任意のPythonによる直接DB更新を封じるサンドボックスではない。

ローカルProviderでは同じSQLite内の一括確定を保証する。外部DB・S3・メール等とまたがる原子性、複数グラフの連携、失敗状態への自動遷移、フロー全体の再開、TemporalやKestraへの自動接続は残課題。既存の購買サンプルと旧準備・確定サンプルを、この方式へ暗黙に移行してはいない。保持期限・GCの残課題も維持する。

```sh
python -m examples.feature_demos.approval_values
python -m pytest tests/runtime/test_transitions.py -q
```
