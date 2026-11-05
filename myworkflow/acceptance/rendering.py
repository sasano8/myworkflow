from myworkflow.generation.documents import document_program
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentOptions:
    title: str = "受入シナリオ"
    report_title: str = "受入テスト結果"
    requirements_link: str | None = None
    business_link: str = "business.md"
    acceptance_link: str = "acceptance.md"
    features_link: str = "features"
    details_link: str | None = None
    data_definitions_link: str = "data-definitions.md"


from myworkflow._internal.markdown import escape as safe


def render_cases(cases, definitions, *, options=None):
    options = options or DocumentOptions()
    lines = [
        "# " + options.title,
        "",
        "featureファイルが正本です。この文書は仕様であり、テスト成功の証明ではありません。",
        "",
    ]
    names = {"Context": "前提", "Action": "操作", "Outcome": "期待結果"}
    for case in cases:
        lines += [
            f'<a id="{case.id}"></a>',
            f"## {safe(case.name)}",
            "",
            f"固定ID：`{case.id}`。基盤："
            + ("Temporal" if "temporal" in case.tags else "ローカルEngine")
            + "。",
            "",
            "対象："
            + "、".join(
                f"[{safe(r)}]({options.business_link}#{r})" for r in case.requirements
            ),
            "",
            f"正本：[ {safe(case.uri)}:{case.line} ]({options.features_link}/{case.uri}#L{case.line})",
            "",
            "| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |",
            "| --- | --- | --- |",
        ]
        for s in case.steps:
            d = definitions.resolve(s["type"], s["text"])
            lines.append(
                f"| {names[s['type']]} | {safe(d.actor)} | {safe(s['text'])} |"
            )
        lines += ["", "<details>", "<summary>操作・検証の実装対応</summary>", ""]
        for s in case.steps:
            d = definitions.resolve(s["type"], s["text"])
            lines.append(
                f"- {safe(s['text'])} → `{d.function.__module__}.{d.function.__name__}`"
            )
        lines += ["", "</details>", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_business(program, registry, cases, *, options=None):
    options = options or DocumentOptions()
    if options.requirements_link and registry:
        program.check(registry)
    text = (
        f"# 業務要件と受入条件の対応\n\n[業務要件]({options.requirements_link})\n"
        if options.requirements_link
        else document_program(
            program,
            registry,
            details_link=options.details_link,
            data_definitions_link=options.data_definitions_link,
        )
    )
    text += "\n## 受入条件との対応\n\n"
    for identity in sorted({r for c in cases for r in c.requirements}):
        text += f'<a id="{identity}"></a>\n### {identity}\n\n'
        for case in cases:
            if identity in case.requirements:
                text += f"- [{safe(case.name)}]({options.acceptance_link}#{case.id})\n"
        text += "\n"
    return text.rstrip() + "\n"
