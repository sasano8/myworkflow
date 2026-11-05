"""Root navigation and separate documents for each requirement catalog."""

from myworkflow._internal.markdown import escape
from myworkflow.generation.workflows import workflow_documents
from myworkflow.generation.data_definitions import (
    render_data_definitions,
    data_definitions_source,
)


def root_catalog_documents(root):
    root.validate()
    lines = [
        f"# {escape(root.name)}：要求カタログ一覧",
        "",
        f"ルートID：{escape(root.id)}",
        "",
        "各要求カタログが名前空間です。同じ固定IDを別の商品で使用できます。",
        "",
        "実行キューやデータ・権限の分離はこの一覧の管理範囲に含みません。",
        "",
        "| 要求カタログID | 名前 | ワークフロー数 |",
        "| --- | --- | --- |",
    ]
    result = {}
    for catalog in root.catalogs:
        directory = "catalogs/" + catalog.id
        lines.append(
            f"| {escape(catalog.id)} | [{escape(catalog.name)}]({directory}/workflows.md) | {len(catalog.workflows)} |"
        )
        notice = f"ルート：{root.name}（{root.id}）／要求カタログ：{catalog.name}（{catalog.id}）。固定IDはこの要求カタログ内で解決します。"
        data_link = "data-definitions.md" if catalog.value_objects else None
        documents = workflow_documents(catalog, notice=notice, data_link=data_link)
        if catalog.value_objects:
            documents["data-definitions.md"] = render_data_definitions(catalog)
            documents["data-definitions.json"] = data_definitions_source(catalog)
        for path, text in documents.items():
            if path.endswith(".md"):
                text += (
                    "\n[要求カタログ一覧]("
                    + ("../../../" if path.startswith("workflows/") else "../../")
                    + "catalogs.md)\n"
                )
            result[directory + "/" + path] = text
    if not root.catalogs:
        lines.extend(["", "要求カタログは未定義。"])
    result["catalogs.md"] = "\n".join(lines) + "\n"
    result["overview.md"] = render_root_overview(root)
    return result


def render_root_overview(root):
    """Derive the overview from declarations in their explicit tuple order."""
    root.validate()
    lines = [
        f"# {escape(root.name)}：業務要求の概要",
        "",
        "> 自動生成：ルートカタログと要求カタログの定義から生成します。文書を直接編集せず、元の定義を変更してください。",
        "",
        f"ルートID：{escape(root.id)}",
        "",
        f"{escape(root.name)}を入口として、{len(root.catalogs)}件の要求カタログをまとめています。",
        "",
        "## 対象業務",
        "",
        "| 要求カタログID | 要求カタログ | ワークフロー | 処理 | 主なステップ |",
        "| --- | --- | --- | --- | --- |",
    ]
    for catalog in root.catalogs:
        workflows = (
            "、".join(
                f"[{escape(w.name)}](catalogs/{catalog.id}/workflows/{w.id}.md)"
                for w in catalog.workflows
            )
            or "未定義"
        )
        pipelines = "、".join(escape(p.name) for p in catalog.pipelines) or "未定義"
        steps = (
            "、".join(escape(s.name) for p in catalog.pipelines for s in p.steps)
            or "未定義"
        )
        lines.append(
            f"| {escape(catalog.id)} | [{escape(catalog.name)}](catalogs/{catalog.id}/workflows.md) | {workflows} | {pipelines} | {steps} |"
        )
    if not root.catalogs:
        lines.extend(["", "要求カタログは未定義。"])
    lines.extend(
        [
            "",
            "## ルートと要求カタログの関係",
            "",
            f"- ルートカタログ：{escape(root.name)}。要求カタログを一覧にまとめます。",
            "- 要求カタログ：ワークフロー、処理、データ、担当ロールを管理する名前空間です。",
            "- 詳細：要求カタログの一覧からワークフロー詳細と共有定義へ進みます。",
            "",
            "定義の固定IDは要求カタログ内で解決します。外から参照するときは、要求カタログIDと定義IDを指定します。",
            "",
            "## 複数カタログで共有するロール",
            "",
        ]
    )
    # Only the very same declaration object is considered shared; equal local IDs
    # alone do not imply that two catalogs share a definition.
    shared = []
    seen = set()
    for catalog in root.catalogs:
        for role in catalog.roles:
            if id(role) in seen:
                continue
            seen.add(id(role))
            owners = [c for c in root.catalogs if any(r is role for r in c.roles)]
            if len(owners) > 1:
                shared.append((role, owners))
    if shared:
        lines.extend(
            [
                "| ロールID | 正式名 | 表示名 | 参照する要求カタログ |",
                "| --- | --- | --- | --- |",
            ]
        )
        for role, owners in shared:
            references = "、".join(
                f"[{escape(c.name)}](catalogs/{c.id}/shared-definitions.md#{role.id})"
                for c in owners
            )
            lines.append(
                f"| {escape(role.id)} | {escape(role.name)} | {escape(role.display_name)} | {references} |"
            )
    else:
        lines.append("共有ロールは未定義。")
    lines.extend(
        [
            "",
            "## 定義の範囲",
            "",
            "この概要にはルートに含まれる要求カタログの宣言内容を表示します。"
            "一覧のステップは宣言順の集約であり、商品間の実行順序や接続を表すものではありません。",
            "",
            "受入条件・実装状況・実行履歴はこのルート定義には含まれていません。"
            "実行負荷・データ・権限の分離は別途設計します。",
            "",
            "## 詳細",
            "",
            "[要求カタログ一覧](catalogs.md)",
            "",
        ]
    )
    return "\n".join(lines)
