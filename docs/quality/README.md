# コード品質の統計

通常のpytestとは別に、リポジトリ直下で実行します。追加依存は本体や通常CIに不要です。

```sh
python -m pip install -e '.[test,acceptance,quality]'
python -m myworkflow.quality.code_metrics
# 今回のように、レビュー用の集計も保存する場合
python -m myworkflow.quality.code_metrics --snapshot docs/quality/code-metrics.md
```

[今回の計測結果](code-metrics.md)。詳細は `artifacts/code-quality/` に出力します。`--output` で変更できます。

| 出力 | 内容 |
| --- | --- |
| metrics.md / metrics.json | 集計・パッケージ別カバレッジ・高複雑度の処理、全関数のCC・ファイル別LOC/SLOC・MI、計測条件 |
| coverage.json / coverage.xml | 行・分岐の網羅と未実行箇所 |
| html/index.html | ファイルごとの未実行行・分岐を閲覧 |
| pytest.xml | 計測対象テストのJUnit結果 |

coverage.pyは `myworkflow/` 全体とサブプロセスを計測します。Radonはネストした関数とメソッドを含め、クラスの平均を関数として二重計上しません。CCランクはA〜Fで高いほど複雑、MIは高いほど保守しやすい目安です。細かい条件は[要件の往復品質](../requirements-quality.md)・受入テストで別に検証します。

GitHub Actionsの独立した **code-quality** ワークフローを手動実行できます。通常のテストには計測を追加していません。テスト失敗時もレポートを出し、終了コードは失敗のまま返します。数値の閾値による合否判定は設けていません。

Temporalのサーバー試験を含める場合は[追加設定](../temporal.md)後に同じコマンドを実行します。SDK・BDDの導入状態、Temporal設定、ソースハッシュ、コミットと変更有無を記録します。スキップ・未実行や条件の異なる結果を同じ網羅率として比較しないでください。保存した集計は計測時点の記録で、pre-commitでは自動更新しません。
