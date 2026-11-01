# 構成と利用方法

## 概要

契約は一度だけ検証して不変のモデルに変換し、実行・型生成・業務概要は同じモデルを読む。受入シナリオはGherkinを正本とし、文書とpytest-bddの実行を結び付ける。業務固有の処理と基盤アダプタは利用側で組み合わせる。

```mermaid
flowchart TD
    source[従来の契約コード SPEC] --> loader[loading / validation]
    declarations[実験用の名前付きクラス宣言] --> compiler[declarations / compile_workflows]
    compiler --> typed[Program.from_catalog]
    typed --> model[不変のContractCatalogモデル]
    compiler --> graph[状態グラフの検査・表・Mermaid図]
    loader --> model
    model --> runtime[Engine]
    model --> codegen[型・骨格生成]
    model --> docs[業務概要生成]
    runtime --> locks[LockProvider]
    runtime --> journal[ExecutionStore]
    runtime --> business[登録された業務処理・Repository・ObjectStore]
    features[Gherkin / 固定ID] --> acceptance[受入モデル・検証]
    model --> acceptance
    acceptance --> readable[受入シナリオ文書]
    acceptance --> plugin[設定可能なpytestプラグイン]
    plugin --> runtime
    plugin --> reports[バージョン付き実行結果]
```

## 業務契約カタログ

型の正式名称は `ContractCatalog`（業務契約カタログ）とする。ワークフロー・パイプライン・ステップ、ロール・トリガー、アーティファクト・バリューオブジェクトの宣言をまとめ、検証・文書生成・実行で共有する。

```python
from myworkflow import ContractCatalog

catalog: ContractCatalog = compiled.catalog
```

状態・トランジションは `compiled.graphs` のStateGraphとして保持し、`CompiledWorkflows` が業務契約カタログとともに束ねる。今回の名称変更で保存形式や実行時の保証範囲は変更しない。従来の `Catalog` は `ContractCatalog` と同じクラスを指す互換名として残す。新しいコードと型注釈では `ContractCatalog` を使う。

## 責務と依存方向

| パッケージ | 責務 | 対応するテスト |
| --- | --- | --- |
| `contracts/` | 業務契約カタログ、状態、値、終了結果・例外、構造上の不変条件 | `tests/contracts/` |
| `compiler/` | 宣言、読込み、名前・参照・データフロー検証、Programの索引 | `tests/compiler/` |
| `runtime/` | Engine・Context・実装登録・変更収集・遷移・補償、実行用Protocol | `tests/runtime/` |
| `storage/` | アーティファクト・blob・準備／確定の型とProtocol | `tests/storage/` |
| `adapters/` | SQLite、一時ファイル、プロセス内ロック、任意のTemporal接続 | `tests/adapters/` |
| `generation/` | 業務要件・データ定義・状態表・図・型・骨格・安全なファイル出力 | `tests/generation/` |
| `build/` | 共通生成と出力先の対応判定、Kestraプレビュー、ビルドCLI | `tests/build/` |
| `acceptance/` | Gherkin、定義、受入文書・レポート、pytestプラグイン | `tests/acceptance/` |
| `quality/` | 元要件と出力・生成型の比較、欠損・充足率の評価 | `tests/quality/` |
| `_internal/` | 複数領域で共有するMarkdownエスケープ、厳密なJSON処理、指紋計算 | 各利用側と `tests/architecture/` |

contractsはcompiler・runtime・表示・保存実装へ依存しない。compilerは生成器へ依存せず、実行と生成が同じコンパイル結果を利用する。storageは保存契約のみを持ち、実装はadaptersへ置く。共通の業務形式の出力はgenerationが所有し、qualityとbuildが利用する。_internalは業務契約や実行処理をimportしない。

これらの依存方向は `tests/architecture/` で検査する。業務アプリの受入テストは `tests/apps/`、複数テストで共有するデータ構築は `tests/_support/` とする。実行や表示が混在していた旧テストファイルは、対象の振る舞いに応じて分割した。

## 公開APIと生成API

`from myworkflow import ContractCatalog, ValueObject, PipelineResult` の公開入口と、既存の `myworkflow.executable` の互換入口は維持する。内部の各モジュールは新しい責務のパッケージへ移し、同じ実装を旧ファイルへ複製しない。

文書生成はProgramのメソッドから分離した。利用側は生成APIを明示して呼ぶ。

```python
from myworkflow.generation.documents import document_program

markdown = document_program(compiled.program, registry)
```

以前の `program.documentation(...)` は上記へ変更する。内部モジュールを直接importしていたコードも、この表のパッケージへ更新する。例えば宣言は `myworkflow.compiler.declarations`、アーティファクトは `myworkflow.storage.artifacts`、Temporalは `myworkflow.adapters.temporal` とする。`myworkflow.build` の設定API・CLIは維持し、骨格生成CLIは `python -m myworkflow.generation.scaffold` に配置する。

`myworkflow` の宣言クラスと `myworkflow.executable` のimportは互換窓口として残す。内部ファイルを分けたことを理由に、固定ID・業務の実行順序・受入条件は変更しない。

## 契約と実装

`Program(SPEC)` が同じContractCatalog系の型へ変換する。購買の正本であるクラス宣言は `compile_workflows(...)` でコンパイルし、`Program.from_catalog(...)` が型付きの同じオブジェクトを直接利用する。[構文と境界](state-graph.md)を参照。読み込んだSPECや `program.spec` のスナップショットを書き換えても、検証済みモデルには影響しない。`program.catalog()` と実行索引は同じ不変のオブジェクトを参照する。

SPECの形は維持している。モデルの索引値は型付きレコードで、初期APIの `record['id']` や `get()` も受け付ける。利用側は属性参照を推奨する。

bool分岐は引き続き線形の条件付きステップで表す。分岐に使った判定値の再代入は静的検証の前提を壊すため拒否する。パイプラインの実行機構は一般的な循環グラフや任意の条件式を実装したものではない。別の状態グラフでは循環を宣言・検査できるが、その実行は明示的に接続するruntime/transitions.pyが担当である。

レジストリの `handlers` は読取り専用。差替えは `fork()` でコピーした上で `replace(id, function)`、削除は `remove(id)` を使う。差替え時も `(ctx: Context) -> None` の契約を検査する。テスト用の変更が元のレジストリへ漏れない。

## 実行の依存を渡す

```python
engine = Engine(
    program,
    registry,
    business_services,
    locks=lock_provider,
    store=execution_store,
)
```

ExecutionStoreには `begin` と `record`、LockProviderには `acquire` を要求する。既存の購買Servicesは互換用の組立て役として残し、`execution_store` と `lock_provider` を公開する。Engineが購買SQLを直接呼ぶことはない。

公開受付は `invoke(binding_id, trigger_id, payload, principal, run_id=...)` を使い、通常の例外を共通終了結果へ変換する。[終了結果と例外API](pipeline-results.md)を参照。内部向けは `run_internal(...)`。旧 `run(...)` は内部実行の互換名で、認可済み受付の代わりにはならない。Principalは信頼された入口で構築する。

Contextは値・業務用の依存・実行情報を分けて保持し、`ctx.execution` で不変の実行メタデータを参照できる。ステップの読書き範囲と値の型の検査を維持する。

## ロックとトランザクション

`InProcessLockProvider` は同じProviderを共有する実行間で有効。Servicesが別インスタンスでもProviderを渡して共有できる。デフォルトで別々に作られたProvider同士は排他しない。

キーは名前空間、アーティファクトID、値の型と値から決定的に生成する。複数項目の順序やPythonのランダム化hashに依存しない。既定は競合時に拒否、timeoutを指定すると有限時間待つ。再入は拒否し、異常終了でも解放する。利用が終わったキーの内部記録を回収する。

これは単一プロセスの機能で、分散排他ではない。SQLiteにもキー単位のアドバイザリーロックはない。SQLiteのBEGIN IMMEDIATE、業務ロック、一意制約は役割が異なる。DBのトランザクションを承認待ち・ネットワーク通信の間まで保持しない。

## 購買の保存と補償

購買Repositoryが申請・承認・添付登録・発注のSQLとトランザクションを管理する。FileObjectStoreがファイルの実体とSQLiteの所有者・バージョン・SHA256・intentを扱い、Recoveryが履歴と保存先を使って明示的な復旧を行う。障害注入・呼出観測は `testing.py` のラッパーへ分離した。

補償は正処理の前に登録し、ステップ境界の入力・得られた値をコピーする。後続処理がContextを書き換えても、以前の補償に使う値を変えない。応答を受け取れなかった外部の結果はContextだけで復元できないため、保存先のintentと所有者・バージョンの照合が必要である。

元の業務エラー、補償エラー、ロック解放・履歴保存の追加エラーを区別する。ExecutionFailedのcauseとstep_idを維持し、追加の失敗はsecondary_errorsへ残す。記録基盤自体が失敗した場合に、履歴が必ず保存されたとは保証しない。

実行状態はRunStatusで扱う。成功した実行の再利用や復旧は拒否する。runningの実行を復旧するには停止済みの明示的な確認が必要で、自動的に停止を判定する機能ではない。

## 受入ツールの設定

アプリケーション側で `AcceptanceConfig` を公開する。契約、操作・検証定義、featureの場所、生成先、文書タイトル・リンク、ハッシュ対象、任意基盤の有効化条件を指定する。

```sh
python -m myworkflow.acceptance --config examples.apps.purchase.acceptance.catalog docs --check
python -m myworkflow.acceptance --config examples.apps.tickets.acceptance.catalog docs --check
python -m pytest tests/apps/purchase -q
python -m pytest tests/apps/tickets -q
```

pytest利用側は `myworkflow.acceptance.pytest_plugin` を読み込み、`acceptance_config` マーカーまたは `--acceptance-config` で設定を指定する。コアの試験だけなら購買のfeatureやpytest-bddを読み込まない。pytest-bddの呼出フレームとExamplesのパラメータへの依存はpytest_bridgeへ隔離している。

結果JSONはschema_version=1。未知の形式、不正な状態、重複ケースID、実行結果のソースハッシュ欠落を拒否する。以前のバージョンなし結果は、そのまま現行の保証には使わず、再実行して作り直す。

ハッシュは設定したソースディレクトリから.py、.json、.toml、.featureを発見して生成する。新しいファイルも自動で含み、Markdownとキャッシュは含まない。依存定義のpyproject.tomlを対象に含め、実行したPython／pytest-bddの版も結果に記録する。外部サービスの設定や全推移依存の同一性を証明するものではない。

実行開始前に対応するハッシュを保持し、結果の比較に使う。複数アプリケーションの結果はケースごとにもハッシュを持つ。未実行・スキップ・失敗・過去結果は引き続き区別する。

## 生成物と互換性

文書・型・骨格は共通の生成処理を通す。全内容を準備してからファイルを置換し、通常の書込みエラーでは既存内容を復元する。複数ファイルに対するOSレベルの一括トランザクションや、突然の電源断までの原子性を保証するものではない。

初回生成は空のディレクトリに限定する。型更新は契約・handlers.pyを上書きしない。文書の `--check` は変更を書き込まない。公開されるモジュール位置を変えた部分は互換importを残し、Registryの直接書換えだけは明示的なAPIへ移行する。

生成文書の業務名・順序・ID・受入条件は維持している。差分は基盤の説明、参照先、第二のサンプル追加によるもの。古い評価文書のテスト件数は当時の記録として残す。

## 未実装の拡張

PostgreSQLのセッション／トランザクション単位のアドバイザリーロック、実S3、認証したHTTP／Signal受付、分散排他、Activity途中停止・キャンセル・期限切れ時の自動復旧は別の機能追加である。今回の整理によって実装済みになったとは扱わない。

## 確認した結果

変更前は全体71件、整理後は全体92件が成功した（いずれもTemporal有効）。この整理の時点ではTemporal結合5件も維持した。SDK・BDDをインストールしない環境ではコア50件が成功した。

購買のfeatureと固定IDは変更せず、4種類の誤実装を検出する試験も残している。新たに契約の不変性、複数申請、Provider共有、補償の値の保持、履歴・解放の二次障害、生成の復元、レポートの準備・後片付け・収集中断、第二の業務を確認した。GitHub上のCI結果と顧客レビューは未確認で、ローカルの成功と区別する。

購買サンプルの整理後は、定義を `examples/apps/purchase/contract.py` に一本化した。旧サンプルは削除し、宣言APIはテスト内の小さな専用データで検証する。模擬Temporal実験も統合し、実際の購買フローに対する結合試験は4件となった。

## アーティファクトの確定境界

[ジョブ管理と準備・確定](artifact-jobs.md)を追加した。中間サーバーへのインターフェースを先に定義し、現在は一時領域のSQLiteで実装する。既存の業務DBと別DBのまま原子性を拡張するものではなく、独立した承認例で検証する。

[ビルドと残課題](build.md)では、Pythonの正本から中間表現と実行基盤向け出力を生成する境界を定義する。SPECは互換用の生成物であり、購買の実行・受入設定は同じ `contract.program` を参照する。

[トランジション実行](transition-execution.md)は `runtime/changes.py` の項目更新と `runtime/transitions.py` の契約検証をEngineへ接続する。状態グラフからのTemporal/Kestra構築や外部副作用の一括確定は行わない。

[データ定義](value-objects.md)は `value_objects.py` がPydanticモデルから生成する。Artifactの型参照と保存レコードの明示的な型接続を使い、入力・宣言された出力・確定前の検証を行う。Contextと保存値はJSONデータで、モデルの利用を全実装へ強制しない。
