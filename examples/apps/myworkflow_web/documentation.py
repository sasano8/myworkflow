"""Generate the requirement inventory and reject missing annotation references."""

from myworkflow import declaration
from myworkflow.contracts.errors import ContractError
from myworkflow._internal.markdown import escape
from . import requirements as r


def requirement_references(catalog, screens):
    annotated = {
        target
        for target in vars(r).values()
        if isinstance(declaration(target), r.Requirement)
    }
    if (
        len(set(r.REQUIREMENTS)) != len(r.REQUIREMENTS)
        or set(r.REQUIREMENTS) != annotated
    ):
        raise ContractError("Every annotated requirement must be registered once")
    specs = tuple(declaration(target) for target in r.REQUIREMENTS)
    ids = {spec.id for spec in specs}
    if not specs or len(ids) != len(specs):
        raise ContractError("Requirement IDs must be unique and nonempty")
    for spec in specs:
        if (
            not spec.id
            or not spec.name.strip()
            or not spec.summary.strip()
            or spec.scope not in {"core", "support"}
        ):
            raise ContractError(f"{spec.id}: invalid requirement annotation")
    references = {}
    for screen in screens:
        for feature in screen.features:
            references.setdefault(feature.id, []).append(screen.id)
    for entity in catalog.entities:
        for identity in entity.extensions.get("requirements", ()):
            references.setdefault(identity, []).append(entity.id)
    if set(references) != ids:
        raise ContractError(
            f"Requirement references differ: missing={sorted(ids - set(references))}, unknown={sorted(set(references) - ids)}"
        )
    return references


def render_requirement_catalog(catalog, screens):
    references = requirement_references(catalog, screens)
    lines = [
        "# 要求カタログ",
        "",
        "requirements.pyのアノテーションから生成する。コードを正本とし、この表は直接編集しない。",
        "",
        "中心となる業務はプロジェクト詳細での開発。周辺機能と分けて表示する。参照の存在は検査するが、意味の充足・実装・受入テストの合格を保証しない。",
        "",
    ]
    for scope, title in (
        ("core", "中心：プロジェクト詳細での開発"),
        ("support", "周辺機能"),
    ):
        lines.extend(
            [
                "## " + title,
                "",
                "| 要求ID | 名前 | 概要 | 対応先 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for target in r.REQUIREMENTS:
            spec = declaration(target)
            if spec.scope == scope:
                lines.append(
                    "| "
                    + " | ".join(
                        map(
                            escape,
                            (
                                spec.id,
                                spec.name,
                                spec.summary,
                                "、".join(references[spec.id]),
                            ),
                        )
                    )
                    + " |"
                )
        lines.append("")
    lines.extend(
        [
            "[業務要件](requirements.md)・[画面一覧](screens.md)・[ワークフロー一覧](workflows.md)",
            "",
        ]
    )
    return "\n".join(lines)
