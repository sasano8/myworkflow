# 購買フローの受入テスト：実装と評価

## 対象と判断

対象は、このフレームワークを使って開発した購買申請サンプルである。フレームワーク自体の型・実行制御・生成処理のテストは別に残す。

今回、Gherkinのfeatureファイルを受入シナリオの正本として採用した。pytest-bddで実行し、同じファイルから業務向けのシナリオ文書を生成する。契約コードは業務構造の正本、featureは具体的な受入条件の正本で、固定IDで関連付ける。生成文書を手で更新しない。

Python宣言との最小比較は `tests/acceptance_tools/test_acceptance.py` で行った。同じ前提・期待結果はPythonの構造でも表現・実行できるが、今回は既存のScenario Outline、Examples、Given／When／Then、pytestのfixtureと結果処理を利用できるGherkinを選んだ。Pythonから同じfeatureを二重生成する方式にはしない。

## 生成物

- [業務概要と受入条件へのリンク](../examples/purchase/docs/business.md)
- [受入シナリオ文書](../examples/purchase/docs/acceptance.md)
- [ローカルの正本](../examples/purchase/acceptance/features/purchase.feature)
- [Temporalの正本](../examples/purchase/acceptance/features/temporal.feature)

文書は仕様であり、テスト結果ではない。結果は別のJSON・Markdownへ出す。Scenario Outlineは6つの具体例へ展開し、例の並べ替えや表示名変更でも維持できるcase IDを持つ。業務の実行者と、時計・障害注入・検証基盤の操作主体を区別する。

## 再現手順

Python 3.14の仮想環境を使い、リポジトリ直下で実行する。

```sh
python -m pip install -e '.[acceptance]'
python -m examples.purchase.acceptance docs --check
python -m pytest -q --acceptance-report artifacts/acceptance.json
python -m examples.purchase.acceptance report artifacts/acceptance.json > artifacts/acceptance.md
```

文書を更新するときだけ `docs --check` ではなく `docs` を実行し、生成差分を確認する。featureや手書きの操作・検証関数は上書きしない。

受入テストだけ、または固定IDを指定して実行することもできる。

```sh
python -m pytest tests/acceptance -q
python -m pytest tests/acceptance --acceptance-case scenario.purchase.schedule -q
```

Temporalを使う場合は任意依存とCLIを用意する。

```sh
python -m pip install -e '.[acceptance,temporal]'
bash scripts/install-temporal-cli.sh /tmp/myworkflow-temporal
RUN_TEMPORAL_ACCEPTANCE=1 TEMPORAL_CLI_PATH=/tmp/myworkflow-temporal/temporal \
  python -m pytest tests/acceptance -q --acceptance-report artifacts/temporal-acceptance.json
```

このクラウドの既存仮想環境は `.venv`、検証したCLIは `/workspace/temporal-tools/temporal` にある。

## シナリオの構造と実行

`scenario.*` タグがシナリオの固定ID、`req.*` タグが業務契約の参照である。Outlineにはcase列を必須とし、シナリオIDと連結してケースIDを作る。

操作・検証の定義は `examples/purchase/acceptance/steps.py`、シナリオ専用コンテキストとアダプタは `world.py` にある。業務ステップのContextと受入テストのWorldは分離する。実際と同じEngine.invokeへ入力・Principalを渡し、期待結果は別のSQL照会で確認する。アプリケーションの出力をそのまま期待値にはしない。

各Thenの検証関数はTrueを返す必要があり、空の関数がNoneを返すと失敗する。ただし、意図的に常にTrueを返すような誤った検証まで自動で見破れるわけではない。検証関数の正しさはレビューと変異試験で補う。

未知の契約ID、未登録または曖昧な操作、重複したシナリオ／ケースID、期待結果のないシナリオを実行前に検出する。すべてのfeatureを先に検証するため、実行対象から外れた不正な定義も見逃さない。未対応のステップ内テーブル・docstringは明示的に拒否し、黙って無視しない。

## 時間・対話・外部障害

ローカルの `ScheduledPurchase` はサンプル側の業務オーケストレーションで、時計を注入できる。日時にはタイムゾーンを必須とする。2030年4月1日10時JSTの直前と、同じ瞬間を示すUTCの日時を使い、発注0件／1件を確認する。実時間で翌日まで待つ必要はない。

ユーザー操作は認証済みと仮定した申請者・承認者のPrincipalで再現する。時計の進行がサンプルのtickを呼ぶ。ローカルのスケジュール自体の永続化やクラッシュ復旧は対象外である。

Temporalの2ケースは実サーバー・実Workerを起動し、Signalで承認／却下し、短い実時間のTimerと子ワークフローを経て同じDB更新を行う。準備・完了は状態や結果を上限付きで待つ。固定秒数のsleepを準備完了の根拠にはしない。絶対日時の境界はローカル時計で検証し、Temporalの時間スキップ環境は今回使っていない。

保存の障害は差し替えアダプタへ注入する。実S3を利用したという意味ではない。補償失敗後は保存基盤を開き直して手動復旧し、別の所有者・バージョンのファイルを消さないことも確認する。

## 品質チェック

Python 3.14.8、pytest 9.2.0、pytest-bdd 9.0.1で検証した。

| 検証 | 結果 |
| --- | --- |
| ローカルの業務受入テスト | 12ケース成功 |
| Temporalを含む業務受入テスト | 14ケース成功（ローカル12＋Temporal2） |
| 通常の全体テスト | 69成功、Temporalの2ケースは明示的にスキップ |
| Temporal有効時の全体テスト | 71成功 |
| 誤実装の検出 | 早すぎる発注、重複発注、却下後の発注、補償漏れの4変異を、対象ケースの失敗として検出 |
| 文書生成 | 同じ正本から決定的に生成し、保存済み出力と一致 |
| 不正な定義 | 未知参照・未接続・曖昧な操作・ID重複・空の検証を検出 |
| 変更追跡 | Outlineの行順序変更、業務名変更でもID維持。元ファイルを上書きしない |
| 日時 | タイムゾーン必須、時刻の逆戻り拒否、JST／UTC同一時刻を確認 |

変異試験はテスト実行時だけ故意に壊したサンプルを使い、期待するAssertionErrorでケースが失敗したことを確認する。通常のテストを無効化・期待値更新して成功扱いにしていない。

型・必須入力など契約から導ける変更は既存の契約検査へ接続する。業務上の期待結果を変えるときは、AI・開発者がfeatureを編集して理由を残す。たとえば発注可能時刻の変更は業務上の判断であり、テスト失敗から期待値を自動修正する対象ではない。

## 結果と未検証の扱い

結果JSONにはケースID、業務契約ID、コミット、未コミット変更の有無、feature・契約・実装／テスト基盤のハッシュ、Python／pytest-bddのバージョンを記録する。passed、failed、skipped、not-runを区別する。単一ケースだけ実行した場合、残りを成功にはせずnot-runにする。

Markdownの結果表示では、定義・実装のハッシュが現在と違う成功結果は「過去結果」と表示する。失敗時にはシナリオIDとトレース、申請状態・保存物件数などの診断を残す。仕様文書へ前回の成功を埋め込んで、現行定義が保証済みであるように見せない。

通常CIへ受入テスト・文書一致検査・結果のArtifact出力を追加した。Temporalは従来どおり手動実行でオンにできる。GitHub上の実行結果は未確認で、ローカルの結果と区別する。

HTTP・ブラウザ、実組織の認証・ロール、実S3、分散排他、Temporalの絶対日時境界・Activity途中停止の完全復旧は未検証。業務概要・受入シナリオが顧客にとって適切かという最終レビューも未実施である。有限のシナリオで全条件を保証したとは扱わない。

## 構成の整理後

上記件数は受入機能追加時点の記録です。その後、受入プラグインをアプリケーション設定方式へ分離し、チケット発行を第二の例として追加しました。結果JSONはschema_version=1、ハッシュ対象は設定ディレクトリから自動発見します。[現在の構成](architecture.md)を参照してください。購買の14ケースと4変異の条件は維持しています。
