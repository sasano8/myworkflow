# コード品質の計測結果

計測：2026-11-01T10:03:55.577678+00:00。対象：`myworkflow/`（サンプル・テストを除く）。

ソースSHA256：`b694f81bd172a9d58243d8a121208fa6709a5eec9b09ab62288bd9fdc6d7196f`。基点コミット：`63e787b7ed5ddd33272c7cc6870af45e504abee9`。未コミット変更：True。

Python 3.14.8 / coverage.py 7.17.0 / Radon 6.0.1。

テスト：成功 330、失敗 0、エラー 0、スキップ 2。終了コード：0。

| 指標 | 値 |
| --- | --- |
| 行カバレッジ | 92.68% (2784/3004) |
| 分岐カバレッジ | 84.96% (1028/1210) |
| 関数・メソッド数（ネストを含む） | 225 |
| 平均循環的複雑度 | 6.76 |
| 複雑度ランク別件数 | {'A': 152, 'B': 31, 'C': 27, 'D': 6, 'E': 5, 'F': 4} |

## パッケージ別カバレッジ

| パッケージ | 行 | 分岐 |
| --- | --- | --- |
| (root) | 100.00% | — |
| _internal | 100.00% | 100.00% |
| acceptance | 90.99% | 81.16% |
| adapters | 89.81% | 86.51% |
| build | 95.21% | 91.94% |
| compiler | 89.77% | 81.72% |
| contracts | 93.67% | 84.06% |
| generation | 95.24% | 90.87% |
| quality | 93.93% | 84.29% |
| runtime | 94.07% | 82.73% |
| storage | 92.11% | 50.00% |

## 複雑度の高い処理（上位15件）

| 処理 | 行 | CC | ランク |
| --- | --- | --- | --- |
| myworkflow/compiler/declarations.py:compile_workflows | 132 | 72 | F |
| myworkflow/compiler/loading.py:load_catalog | 6 | 59 | F |
| myworkflow/contracts/validation.py:validate_catalog | 8 | 50 | F |
| myworkflow/build/compiler.py:compile_outputs | 60 | 44 | F |
| myworkflow/quality/metrics.py:source_coverage | 50 | 36 | E |
| myworkflow/acceptance/gherkin.py:load_cases | 5 | 34 | E |
| myworkflow/compiler/validation.py:validate_flow | 37 | 33 | E |
| myworkflow/quality/runner.py:run_case | 41 | 32 | E |
| myworkflow/generation/business.py:business_to_spec | 52 | 31 | E |
| myworkflow/contracts/state_graph.py:StateGraph.validate | 40 | 30 | D |
| myworkflow/generation/documents.py:render | 5 | 29 | D |
| myworkflow/quality/interfaces.py:check_interfaces | 7 | 26 | D |
| myworkflow/generation/data_definitions.py:_constraints | 45 | 25 | D |
| myworkflow/runtime/engine.py:Engine._run_or_raise | 73 | 24 | D |
| myworkflow/compiler/validation.py:validate_names | 12 | 23 | D |

詳細な関数別CC・ファイル別LOC/SLOC・保守性指標はmetrics.json、未実行行はcoverage.json・HTMLを参照。
CCは分岐経路数の目安、MIは静的な保守性指標です。数値だけで品質や業務条件の網羅を保証しません。
サブプロセスも計測します。利用した任意依存・Temporal設定はmetrics.jsonに記録し、構成の違う結果を単純比較しません。
