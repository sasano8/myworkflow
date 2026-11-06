# myworkflow Webアプリ

コードから、いつでも再現できる業務要件定義書。

中心となる業務は、プロジェクト詳細での「対話による要件入力 → コード反映 → ビルド・検証 → 文書・差分確認」。一覧・作成・削除・テンプレート管理は周辺機能として扱う。処理本体・画面・外部連携は未実装。

| 正本となるコード | 内容 |
| --- | --- |
| [requirements.py](requirements.py) | 要求ID・概要・中心／周辺の区分をクラスへ注釈として定義 |
| [contract.py](contract.py) | 注釈付きワークフロー・パイプラインと接続 |
| [steps.py](steps.py) | 注釈付きステップの処理概要。実装は未着手 |
| [definitions.py](definitions.py) | 注釈付きロール・入出力物。内部項目・制約は未決 |
| [screens.py](screens.py) | 注釈付き要件を参照する画面機能とワークフローの対応 |

[要求カタログ](docs/requirement-catalog.md)・[ワークフロー一覧](docs/workflows.md)・[業務要件](docs/requirements.md)・[画面一覧](docs/screens.md)は、コードから生成する。変更は注釈付きコードへ反映し、`python -m scripts.generate_docs`で再生成する。要件をMarkdownへ二重転記しない。

未決の実装方式・提案・受入条件の候補は[検討メモ](design-notes.md)に残す。承認された内容はコード宣言へ取り込み、実装保証や受入テストの合格と区別する。
