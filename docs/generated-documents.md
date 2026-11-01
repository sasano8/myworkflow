# 生成文書とpre-commit hook

コミット時に現在の宣言から文書・型を生成し、決められた出力ファイルだけを自動でステージする。通常のコードレビューで生成差分も確認する。

## 有効化

Python 3.14の仮想環境にプロジェクトと受入文書生成の依存を入れ、このcloneで一度hookを設定する。

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install '.[test,acceptance]'
sh scripts/install-hooks.sh
```

Gitはclone先でhook設定を自動継承しないため、新しいcloneでは設定を実行する。既存のcore.hooksPathや実行可能なpre-commit hookがあれば上書きせず停止する。その場合は既存hookから生成コマンドを呼ぶ形で接続する。

hookは `.venv/bin/python`、存在しなければ `python3` を使用する。別の環境を使う場合は `MYWORKFLOW_PYTHON=/path/to/python` で指定する。Temporal SDKやサーバーは生成に不要だが、pytest-bddとGherkinの依存は必要である。

## コミットの流れ

```sh
git add examples/purchase/contract.py examples/purchase/value_objects.py
git commit -m "Update purchase contract"
```

hookが `python -m scripts.generate_docs --hook` を呼び、生成物を更新して自動でステージする。ソースコード・Gherkin・無関係なファイルを勝手にステージしない。

| 状況 | 動作 |
| --- | --- |
| 生成に使うPython・feature・設定等がステージ済み | 生成とステージを行い、コミットを続行 |
| ソースに未ステージの変更や未追跡ファイルがある | 一部だけのソースから文書を作らないよう、書込み前にコミットを停止 |
| 生成ファイルに、再生成で消える未ステージの編集がある | 編集を上書きせず停止。確認後、明示的な生成コマンドで更新できる |
| 未ステージの生成物が既に正しい内容 | その生成物をステージ |
| 生成・型・宣言検証に失敗 | コミットを停止 |

部分コミットで一時的に別の宣言を生成する機能はない。生成入力はまとめてステージする。既存の独立したテスト期待値を最新実装から自動で書き換えない。

## 出力対象

このリポジトリに登録したサンプルを対象にする。別のアプリを追加する場合は `scripts/generate_docs.py` の対象へ明示する。

| 範囲 | 自動生成するもの |
| --- | --- |
| `examples/purchase/` | interfaces.py、requirements.md、data-definitions.md/json、Kestraプレビュー |
| `examples/approval-values/` | requirements.md、data-definitions.md/json |
| `examples/declarative_review*` | 業務概要・状態表・業務フロー図 |
| 購買・チケットのacceptanceディレクトリ | business.md、acceptance.md |
| 原文・qualityの採点用入力／期待値・テストの条件 | 自動更新しない |
| README・設計文書 | 自動更新しない |

生成の一致は、業務上の意味や期待値が正しいという証明ではない。業務条件の正しさは、原文との独立した比較・受入テスト・レビューで確認する。

## Markdownの表示

バリューオブジェクトの生成Markdownはすべて簡易表とする。意味・型・必須項目・制約・既定値・例・補足ルールを示し、詳細JSON Schemaのコードブロックは含めない。ネストした項目はパスで表し、複雑な条件はJSONを参照する。完全な機械可読定義はdata-definitions.jsonへ残す。業務概要、受入シナリオ、手書き文書の表示形式は、この変更の対象外である。

## 手動生成とCI

```sh
.venv/bin/python -m scripts.generate_docs
.venv/bin/python -m scripts.generate_docs --check
```

手動生成はステージしない。`--check` は書込みやステージを行わず、不一致で失敗する。CIでも同じコマンドの `--check` を実行するため、hookが未設定でも出力の更新漏れを検出する。
