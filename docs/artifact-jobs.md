# ジョブIDによるアーティファクトの準備と確定

## 目的とインターフェース

パイプラインはアーティファクトの読込み・検証・変更の準備を行い、最後に共通の確定インターフェースを呼ぶ。中間サーバーを用意せず、Pythonの `ArtifactCoordinator` Protocolと、ローカルのデフォルト実装を追加した。

| 操作 | 戻り値と意味 |
| --- | --- |
| `read(key)` | 確定済みの値とバージョン。存在しなければNone |
| `prepare(job_id, writes)` | 準備を永続化し、ジョブの状態を返す。業務から見える確定値は変えない |
| `commit(job_id)` | バージョンを確認し、全アーティファクトと確定結果を一括保存する |
| `status(job_id)` | 準備済み・確定済み・破棄済みと、確定したバージョンを照会する。未登録ならNone |
| `discard(job_id)` | 未確定の準備を破棄状態にして、そのジョブのファイルを削除する |

`ArtifactWrite(key, value, expected_version)` で変更を指定する。`expected_version=0` は新規作成、正の整数はそのバージョンからの更新を要求する。単純な「存在すれば上書き」にはしない。

宣言のArtifact IDが情報の種類を識別する一方、このProviderのkeyは個別の保存対象を識別する。ジョブIDは確定依頼一件の識別子であり、申請IDとは別にする。同じ申請へ次の操作を行うときは新しいジョブIDを使う。

業務状態もアーティファクトとして保存する。例えば `application:123` に申請データ、`state:123` に状態IDを持たせ、同じジョブで確定する。Protocolを将来HTTP等で実装すれば、パイプラインを変えずに中間サーバーへ接続できる。現在は通信アダプターやサーバーを実装していない。

## 楽観ロックと排他ロック

楽観ロックは読込み時のバージョンを確定時に照合する。排他ロックは処理前に同じ対象への同時処理を待機・拒否する。別の仕組みであり、必要なら併用できる。現在のCoordinatorでは `ArtifactWrite.expected_version` による楽観ロックを実装済み。

次は二つの操作が同じバージョンを読み、先に確定した操作だけが成功する例。保存先を一時ディレクトリに限定しているため、単独で実行できる。

```python
from tempfile import TemporaryDirectory
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.artifact_jobs import ArtifactConflict, ArtifactWrite

with TemporaryDirectory() as root:
    coordinator = TemporaryArtifactCoordinator(root=root, namespace="optimistic-example")
    coordinator.prepare("create", (
        ArtifactWrite("application:123", {"status": "waiting"}, expected_version=0),
    ))
    coordinator.commit("create")

    # 両方が同じ確定済みバージョン1を読む。
    first = coordinator.read("application:123")
    second = coordinator.read("application:123")
    coordinator.prepare("approve", (
        ArtifactWrite("application:123", {**first.value, "status": "approved"}, first.version),
    ))
    coordinator.prepare("reject", (
        ArtifactWrite("application:123", {**second.value, "status": "rejected"}, second.version),
    ))

    coordinator.commit("approve")  # バージョン2になる。
    try:
        coordinator.commit("reject")  # 想定1に対して実際は2なので競合。
    except ArtifactConflict:
        coordinator.discard("reject")
    else:
        raise AssertionError("古いバージョンの更新は拒否されるべき")

    current = coordinator.read("application:123")
    assert current.value["status"] == "approved"
    assert current.version == 2
```

競合したジョブの変更は一括して反映されない。再処理する場合は最新値を読み直し、業務条件を再検証して新しいジョブIDで準備する。古い変更のバージョンだけを書き換えて強制適用しない。競合は技術的な再試行で解決できるとは限らず、利用者へ再確認を求める方針も業務ごとに決める。

検査対象は書込みに指定したキーである。読んだだけの別アーティファクトや外部DB・ストレージまで、自動的に競合検査するものではない。

## 利用側APIの方針

変更をまとめる高水準APIは `ctx.changes` と呼ぶ。[トランジション実行](transition-execution.md)を接続したEngineで使用できる。承認待ち等の業務状態と混同しないためである。状態も通常の項目更新として表し、状態だけを更新する `set_state` は導入しない。

```python
# applicationはctx.changes.subject。状態値には宣言した固定IDを使う。
ctx.changes.update(application, approved_by=ctx.actor, status=Approval.approved.id)
```

`ctx.changes` は読込み時のバージョンを変更予定へ自動的に引き継ぎ、確定時の楽観ロックに使用する。Engineが開始状態・ガードと成功後の状態を検証し、最後に変更全体を確定する。

この操作は変更予定の作成であり、DBへの確定ではない。最後にprepare・commitする保存境界は維持する。現在の低水準APIでは、変更後の値を `ArtifactWrite` で指定する。高水準APIでは、既存JSONレコードの状態フィールドを対象にする。状態が別アーティファクトにある旧サンプルを暗黙に変換しない。

## デフォルトの一時領域

```python
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.artifact_jobs import ArtifactWrite

coordinator = TemporaryArtifactCoordinator(namespace='purchase')
coordinator.prepare('approval-job-001', (
    ArtifactWrite('application:123', {'owner': 'alice', 'approved_by': 'bob'}),
    ArtifactWrite('state:123', 'approved'),
))

# この時点ではread('state:123')はNone。準備はまだ公開されていない。
coordinator.commit('approval-job-001')
receipt = coordinator.status('approval-job-001')
```

既定の保存先は `tempfile.gettempdir()/myworkflow-artifacts/<namespaceのSHA256>/`。業務JSON・状態・準備・確定結果・ファイルの参照メタデータを `coordinator.sqlite` に保存する。blobの実体は `jobs/<job_idのSHA256>/<nameのSHA256>-<内容のSHA256>` に保存し、DBには格納しない。論理ジョブIDやファイル名をそのままパスへ挿入しない。同じ環境で同じ名前空間を指定すれば、別のインスタンス・プロセスから同じジョブを参照できる。

`root=...` で親ディレクトリを変更できる。アプリケーションごとに名前空間を分ける。同じジョブIDでも、名前空間またはrootが異なれば別のジョブになる。Pythonオブジェクトの破棄時には保存先を削除しない。

一時領域はOSや環境の清掃・再作成で消える。別ホスト・別コンテナから自動的に共有できる領域でもない。長期間の承認待ちや本番の復旧には、保持期間を確保した保存先または別Providerが必要になる。期限切れ・自動清掃・容量制限・汎用的なデータ形式の移行は未実装。旧JSON保存領域にはstorage区分の列を追加し、既存JSONを維持する。

## blobをファイルとして扱う

```python
coordinator = TemporaryArtifactCoordinator(namespace='purchase')
attachment = coordinator.blobs.stage_file('upload-job-001', 'quotation.pdf', '/path/to/quotation.pdf')
coordinator.prepare('upload-job-001', (
    ArtifactWrite('quotation:123', attachment),
    ArtifactWrite('state:123', 'quotation-ready'),
))
coordinator.commit('upload-job-001')

reference = coordinator.read('quotation:123').value
with coordinator.blobs.open(reference) as stream:
    # 必要な分だけ読む。ファイル全体をメモリへ載せる必要はない。
    chunk = stream.read(1024 * 1024)
```

`BlobStore` Protocolを追加し、ローカル実装はCoordinatorの `blobs` へ接続する。`stage_file` は元ファイルを変更せずコピーする。`stage_stream` はバイナリストリームを受け取り、1MiBずつコピー・SHA256計算する。blob本体をSQLiteへ変換・格納する処理や、独自の固定サイズ上限は設けない。ディスク容量やOS・保存基盤の制約までなくなるわけではない。

`BlobRef` はジョブID・論理ファイル名・SHA256・サイズだけを持ち、Providerの名前空間内で解決する。これを `ArtifactWrite.value` へ直接渡す。通常のJSONに任意のファイルパスを埋めただけでは、ファイルの所有・公開・削除の管理対象にはならない。

ファイルはprepareより前にステージでき、`blobs.list_files(job_id)` で一覧を確認できる。この時点では `status(job_id)` はNoneの場合がある。prepare後は新しいファイルを追加できない。同じ名前と同じ内容の再送は同じ参照へ戻り、違う内容では拒否する。

commit前にファイルの存在・サイズ・SHA256を検証する。大きいファイルの検証はDBの確定トランザクションの外で行う。commitでファイルを移動せず、DBのファイル参照・業務JSON・状態・確定記録だけを一括公開する。参照が公開されるまで業務上は未確定であり、信頼された処理は `blobs.open` で準備中の内容も読める。

破棄はまずDBにdiscardedを記録し、そのジョブのファイルを削除する。削除途中で停止した場合はdiscardを再実行できる。prepare前のステージファイルも破棄できる。確定済みジョブの破棄や、他ジョブが所有するBlobRefの公開は拒否する。確定済みファイルは自動削除しないため、別途保管・GC方針が必要。

`open` は参照メタデータとサイズを確認する。利用側が保存後の完全性も照合する場合は `blobs.verify(reference)` を明示してSHA256を検証する。既に公開したファイルを管理外の処理で消す・改変することまで防ぐ仕組みではない。

## ジョブの約束

- 一つのジョブIDは一つの変更内容に固定する。同じ変更の再送は同じジョブとして扱い、変更が異なれば `JobConflict` にする。
- 確定を再送してもバージョンを再加算せず、最初の確定結果を返す。後続ジョブが同じアーティファクトを更新しても、過去の確定結果は変えない。
- 想定バージョンが変わっていたら `ArtifactConflict` にし、どの変更も公開しない。準備は照会・破棄できる状態で残す。
- 破棄は繰り返せるが、確定済みを破棄することや、破棄済みを確定することは拒否する。
- 確定・破棄済みジョブへの同一prepareは、その最終状態を返す。最終状態を準備済みへ戻すものではない。別の依頼には新しいジョブIDを使う。

ジョブIDは実行基盤の「試行ごとのID」ではなく、同じ確定依頼を識別するIDとして安定させる。サンプルでは `Context.run_id` を使う。別タスクや別試行へ引き継ぐ際には、同じ論理ジョブIDを明示して渡す必要がある。

## パイプラインからの利用

[承認サンプル](../examples/prepared_approval/application.py)は、既存Engineとクラス宣言を使って次を実行する。

1. 申請と状態を読み、承認待ち・自己承認禁止を確認する。
2. 変更予定の申請データと状態を、読込み時のバージョンを付けてprepareする。
3. 最後のステップでcommitし、共通の終了コードとメッセージを返す。

状態値は宣言したPythonの状態オブジェクトの固定IDを参照する。Providerへ業務上の判断ロジックを埋め込まない。

```sh
python -m examples.prepared_approval
python -m pytest tests/test_artifact_jobs.py -q
```

停止後は同じroot・名前空間でProviderを開き直し、`status(job_id)` で確認する。準備済みなら同じジョブを確定または破棄し、確定済みならその結果を採用する。確定の応答が失われても、結果照会と同じIDでの再送ができる。

これは確定Providerの再開であり、既存Engineの実行履歴を自動再開する機能ではない。Engineは同じrun_idの再利用を拒否する。受入・認証を省略して任意の利用者へcommitを公開することも意図していない。現在のProviderは信頼された呼出し元向け。

## 保証する保存境界

ローカル実装は短い `BEGIN IMMEDIATE` トランザクションを使う。全ての想定バージョンを確認した後、アーティファクト・業務状態・確定結果を同じSQLite DB内で反映する。準備と確定の間にDBトランザクションやロックを持ち続けない。ロックはDB単位であり、分散したキー単位のアドバイザリーロックではない。

一括確定できるのはこのProviderのDB内である。既存の購買RepositoryのDB、外部DB、S3、メールやAPIへまたがる原子性は提供しない。業務データはJSON、blobはBlobRefを通したファイルとして扱う。ファイルを先に完成させ、公開参照をDBで確定する方式であり、ファイルシステムとDBをまたぐ一般的なトランザクションではない。ステージファイルの作成後にメタデータ保存が失敗すると未参照ファイルが残る場合があり、ジョブの破棄で回収する。任意の外部ファイルやS3との原子性は保証しない。

Engineの実行履歴も別の保存境界にある。アーティファクトのcommitが成功した後、Engineの履歴保存や応答が失敗する場合はあり得る。そのとき終了コードだけから未確定と判断せず、Coordinatorのジョブ状態を照会する。

既存の購買サンプルの模擬S3もFileObjectStoreへ変更し、本文はファイル、所有者・バージョン・SHA256・intentはSQLiteで管理する。新Coordinatorへの一括移行ではなく、補償モデルを保ったまま実体の保存先を分離したもの。旧body列に内容が残るサンプルDBは自動削除・暗黙変換せず、明示的なエクスポートが必要というエラーにする。汎用の状態遷移実行・フロー全体の自動再開・Kestraマニフェスト生成を、この追加で完成したとは扱わない。

## 確認する品質

契約テストでは、準備中の非公開、値のコピー、再送と内容不一致、確定済み結果の安定、競合、破棄の状態制約を確認する。状態の書込み時にDBエラーを注入し、先に書き込んだデータと確定結果もロールバックされることを検証する。

複数の接続から同じバージョンの確定を競わせ、一つだけ成功すること、別プロセスで準備し終了後にさらに別プロセスから確定できることも確認する。サンプルの受入相当の検査では、正常な承認、確定直前の停止と明示的な復旧、自己承認の拒否を扱う。

ファイルの契約テストでは、分割コピー、DBに本文が入らないこと、ジョブ単位の再送・破棄・所有範囲、欠損・改変時の確定拒否、公開失敗後のファイル保持、別プロセスからの確定も確認する。


## 保持・削除ポリシー（未実装）

保持方針は業務上の宣言として持ち、削除対象の判定と実削除はProvider、実行周期はcron等の定期ジョブまたはストレージのLifecycleで扱う。現時点では方針の宣言・自動削除・定期GCは実装していない。[残タスク](poc-plan.md#アーティファクトの保持削除ポリシー未着手)として管理する。

| 用途 | 削除条件の方針 |
| --- | --- |
| DB反映用の一時データ | 確定済みで復旧に不要となった後。一時データだけを削除し、反映先の業務データは保持する |
| 正式保管するファイル | 自動削除の対象外 |
| 一時アップロード | 宣言した起点から一定期間後。期間は用途ごとに定義する |
| 失敗・補償待ち・結果不明のデータ | 期限だけで消さず、復旧判断まで保持する |

一時アップロードを正式保管へ昇格するときは保持方針を変更する。S3では保存先やタグ等で区別し、アップロード時の期限が正式保管へ持ち越されないようにする。正式保管への昇格や参照追加と削除処理の競合も扱う。

ファイル本体と、確定結果・冪等性記録・削除履歴等の小さな管理情報は、別の保持期間を持つ。管理情報を削除すると同じジョブIDでの再送や結果照会の保証に影響するため、その有効期間も合わせて定義する。削除は対象の所有範囲と参照を確認し、途中停止後に安全に再実行できる方式とする。
