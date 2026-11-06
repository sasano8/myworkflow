"""Refresh current generated examples; reviewed requirements and test oracles are inputs."""

from myworkflow.generation.documents import document_program
import argparse
from pathlib import Path
import subprocess
import sys

from myworkflow.generation.files import write_outputs

ROOT = Path(__file__).resolve().parents[1]


def outputs():
    from examples.apps.purchase import contract, handlers
    from examples.apps.purchase.build import BUILD as PURCHASE
    from examples.feature_demos.approval_values.build import BUILD as VALUES
    from examples.feature_demos.prepared_approval.build import BUILD as PREPARED
    from examples.feature_demos.declarative_review.contract import (
        compiled,
        documentation,
    )
    from examples.apps.purchase.acceptance.catalog import CONFIG as purchase_acceptance
    from examples.apps.tickets.acceptance.catalog import CONFIG as ticket_acceptance
    from myworkflow.acceptance.rendering import render_business, render_cases
    from myworkflow.build.cli import compile_outputs
    from myworkflow.generation.flowcharts import render_business_flow

    purchase = compile_outputs(PURCHASE, target="temporal")
    preview = compile_outputs(PURCHASE, target="kestra", workflows=("w.attach",))
    values = compile_outputs(VALUES, target="temporal")
    result = {
        "examples/apps/purchase/interfaces.py": purchase["interfaces.py"],
        "examples/apps/purchase/docs/requirements.md": document_program(
            contract.program,
            handlers.registry,
            details_link="../../../../docs/execution-design.md",
        ),
        "examples/apps/purchase/docs/data-definitions.md": purchase[
            "data-definitions.md"
        ],
        "examples/apps/purchase/docs/data-definitions.json": purchase[
            "data-definitions.json"
        ],
        "examples/apps/purchase/docs/kestra-attachment.yaml": preview["manifest.yaml"],
        "examples/feature_demos/approval_values/docs/requirements.md": values[
            "requirements.md"
        ],
        "examples/feature_demos/approval_values/docs/data-definitions.md": values[
            "data-definitions.md"
        ],
        "examples/feature_demos/approval_values/docs/data-definitions.json": values[
            "data-definitions.json"
        ],
        "examples/feature_demos/prepared_approval/docs/requirements.md": compile_outputs(
            PREPARED, target="temporal"
        )["requirements.md"],
        "examples/feature_demos/declarative_review/docs/requirements.md": documentation(),
        "examples/feature_demos/declarative_review/docs/flow.md": render_business_flow(
            compiled.graphs[0], compiled.catalog
        ),
    }
    for config in (purchase_acceptance, ticket_acceptance):
        cases = config.cases()
        directory = config.output_directory.relative_to(ROOT)
        result[str(directory / "business.md")] = render_business(
            config.program, config.registry, cases, options=config.documents
        )
        result[str(directory / "acceptance.md")] = render_cases(
            cases, config.definitions, options=config.documents
        )
    from myworkflow.generation.data_definitions import (
        data_definitions_source,
        render_data_definitions,
    )

    ticket_catalog = ticket_acceptance.program.model
    result["examples/apps/tickets/docs/data-definitions.md"] = render_data_definitions(
        ticket_catalog
    )
    result["examples/apps/tickets/docs/data-definitions.json"] = (
        data_definitions_source(ticket_catalog)
    )

    from myworkflow.generation.workflows import workflow_documents

    views = {
        "examples/apps/purchase/docs": (
            contract.program.model,
            PURCHASE.compiled.graphs,
            purchase_acceptance.cases(),
        ),
        "examples/apps/tickets/docs": (
            ticket_acceptance.program.model,
            (),
            ticket_acceptance.cases(),
        ),
        "examples/feature_demos/approval_values/docs": (
            VALUES.compiled.catalog,
            VALUES.compiled.graphs,
            (),
        ),
        "examples/feature_demos/prepared_approval/docs": (
            PREPARED.compiled.catalog,
            PREPARED.compiled.graphs,
            (),
        ),
        "examples/feature_demos/declarative_review/docs": (
            compiled.catalog,
            compiled.graphs,
            (),
        ),
    }
    for directory, (catalog, graphs, cases) in views.items():
        data_link = (
            "data-definitions.md"
            if directory + "/data-definitions.md" in result
            else None
        )
        for name, text in workflow_documents(
            catalog, graphs=graphs, cases=cases, data_link=data_link
        ).items():
            result[directory + "/" + name] = text
    from examples.feature_demos.manual_receipt.contract import (
        catalog as manual_catalog,
        graph as manual_graph,
        DOCUMENTATION_NOTICE,
    )

    for name, text in workflow_documents(
        manual_catalog, graphs=(manual_graph,), notice=DOCUMENTATION_NOTICE
    ).items():
        result["examples/feature_demos/manual_receipt/docs/" + name] = text
    from examples.apps.myworkflow_web.contract import (
        CATALOG as WEB_CATALOG,
        NOTICE as WEB_NOTICE,
        compiled as WEB_COMPILED,
    )
    from examples.apps.myworkflow_web.screens import SCREENS as WEB_SCREENS
    from examples.apps.myworkflow_web.documentation import render_requirement_catalog
    from examples.apps.purchase.screens import SCREENS
    from myworkflow.generation.screens import render_screens

    result["examples/apps/purchase/docs/screens.md"] = render_screens(
        SCREENS, contract.program.model
    )
    result["examples/apps/myworkflow_web/docs/requirement-catalog.md"] = (
        render_requirement_catalog(WEB_CATALOG, WEB_SCREENS)
    )
    for name, text in workflow_documents(WEB_CATALOG, notice=WEB_NOTICE).items():
        result["examples/apps/myworkflow_web/docs/" + name] = text
    result["examples/apps/myworkflow_web/docs/screens.md"] = render_screens(
        WEB_SCREENS, WEB_CATALOG
    )
    result["examples/apps/myworkflow_web/docs/requirements.md"] = document_program(
        WEB_COMPILED.program
    ).replace("# 業務要件\n", "# 業務要件\n\n" + WEB_NOTICE + "\n", 1)

    from examples.feature_demos.cron_reporting.contract import (
        CATALOG as CRON_CATALOG,
        SCHEDULE,
    )
    from examples.feature_demos.cron_reporting.application import (
        program as cron_program,
        registry as cron_registry,
    )
    from myworkflow.generation.schedules import render_schedules

    cron_directory = "examples/feature_demos/cron_reporting/docs/"
    for name, text in workflow_documents(CRON_CATALOG, schedules=(SCHEDULE,)).items():
        result[cron_directory + name] = text
    result[cron_directory + "requirements.md"] = document_program(
        cron_program, cron_registry
    )
    result[cron_directory + "schedules.md"] = render_schedules(
        (SCHEDULE,), CRON_CATALOG
    )
    result[cron_directory + "example.crontab"] = (
        "# Cronie crontab example. Review deployment paths before installing.\n"
        f"CRON_TZ={SCHEDULE.timezone}\n"
        f"{' '.join(SCHEDULE.expression.split())} cd /opt/myworkflow && .venv/bin/python -m examples.feature_demos.cron_reporting --database /var/lib/myworkflow/daily-report.db\n"
    )
    labels = {
        "schedules.md": "cron式・タイムゾーン・起動先の定義",
        "example.crontab": "Cronie用crontab例（未登録）",
        "screens.md": "画面IDごとの画面単体機能・操作契機・ワークフロー呼出",
        "workflows.md": "ワークフロー一覧・未配置の定義",
        "shared-definitions.md": "処理・ロール・データの共有定義",
        "requirements.md": "業務要件・型・実装対応",
        "requirement-catalog.md": "注釈付きの要件と画面・処理の対応",
        "business.md": "業務要件と受入条件の対応",
        "acceptance.md": "受入シナリオ",
        "data-definitions.md": "データ定義（1項目1行）",
        "data-definitions.json": "機械可読のデータ定義・JSON Schema",
        "flow.md": "業務フロー図",
        "kestra-attachment.yaml": "Kestra説明用プレビュー（配備不可）",
    }
    catalogs = {
        "examples/apps/purchase/docs": "購買",
        "examples/feature_demos/cron_reporting/docs": "cronによる日次レポート",
        "examples/feature_demos/approval_values/docs": "承認・バリューオブジェクト例",
        "examples/feature_demos/declarative_review/docs": "申請審査",
        "examples/feature_demos/prepared_approval/docs": "アーティファクトの準備・確定",
        "examples/apps/tickets/docs": "チケット発行",
        "examples/apps/myworkflow_web/docs": "myworkflow Webアプリ（要件定義・未実装）",
        "examples/feature_demos/manual_receipt/docs": "メールで届いた申請書の人手受付",
    }
    source_files = {
        "purchase": "contract.py",
        "tickets": "contract.py",
        "myworkflow_web": "contract.py",
        "declarative_review": "contract.py",
        "approval_values": "application.py",
        "prepared_approval": "application.py",
        "manual_receipt": "contract.py",
        "cron_reporting": "contract.py",
    }
    for directory, name in catalogs.items():
        files = sorted(
            Path(file).name for file in result if str(Path(file).parent) == directory
        )
        purpose = (
            "業務アプリのサンプル"
            if directory.startswith("examples/apps/")
            else "機能単位の技術検証"
        )
        lines = [
            f"# {name}：{purpose}",
            "",
            "このディレクトリは宣言コードから自動生成する。変更は元のコード・受入シナリオへ反映する。",
            "",
            f"宣言コード：[{source_files[Path(directory).parent.name]}](../{source_files[Path(directory).parent.name]})",
            "",
            "[ワークフロー一覧から読む](workflows.md)",
            "",
            "| ドキュメント | 内容 |",
            "| --- | --- |",
        ]
        if directory in (
            "examples/apps/purchase/docs",
            "examples/apps/myworkflow_web/docs",
        ):
            lines[-2:-2] = ["画面機能定義：[screens.py](../screens.py)", ""]
        lines.extend(f"| [{file}]({file}) | {labels[file]} |" for file in files)
        if directory == cron_directory.rstrip("/"):
            lines.extend(
                [
                    "",
                    "## 手動で1回実行",
                    "",
                    "リポジトリのルートから実行します。集計結果はサンプルの固定本文です。",
                    "",
                    "```sh",
                    ".venv/bin/python -m examples.feature_demos.cron_reporting --database /tmp/myworkflow-daily-report.db --date 2030-04-01",
                    "```",
                    "",
                    "`--date` を省略すると、定義したタイムゾーンの前日を対象にします。"
                    "対象日を主キーに保存するため、同じ日の再実行でもレポートは1件です。実行履歴は起動ごとに記録します。",
                    "",
                    "## 定期実行",
                    "",
                    "[example.crontab](example.crontab) はCRON_TZをサポートするCronie向けの例です。"
                    "式とタイムゾーンはスケジュール定義から生成します。"
                    "配置先 `/opt/myworkflow` とDB保存先を環境に合わせて変更し、外部のcronへ登録してください。"
                    "このサンプルの生成・テストでは登録しません。",
                    "",
                    "cronが停止していた期間の追いつき実行は自動化しません。必要な対象日を `--date` で指定して再実行します。"
                    "DB書込みが競合・失敗した場合はコマンドが失敗します。分散ロックや通知はこの例の対象外です。",
                ]
            )
        result[directory + "/README.md"] = "\n".join(lines) + "\n"
    from examples.feature_demos.product_catalogs.root import ROOT as PRODUCT_ROOT
    from myworkflow.generation.catalogs import root_catalog_documents

    for name, text in root_catalog_documents(PRODUCT_ROOT).items():
        result["examples/feature_demos/product_catalogs/docs/" + name] = text
    result["examples/feature_demos/product_catalogs/docs/README.md"] = (
        f"# {PRODUCT_ROOT.name}：商品別の要求カタログ\n\n"
        "このディレクトリは宣言コードから自動生成する。\n\n"
        "ルート：[root.py](../root.py)／保険：[insurance.py](../insurance.py)／融資：[loan.py](../loan.py)／共通：[shared.py](../shared.py)\n\n"
        "[銀行の概要から読む](overview.md)／[要求カタログ一覧](catalogs.md)\n"
    )
    return result


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def _input(path):
    return (
        path == "pyproject.toml"
        or path.startswith(".githooks/")
        or (
            path.startswith(("myworkflow/", "examples/", "scripts/"))
            and Path(path).suffix in (".py", ".feature", ".toml", ".sh")
        )
    )


def pending_inputs(root, excluded):
    unstaged = {
        p.decode() for p in git(root, "diff", "--name-only", "-z").split(b"\0") if p
    }
    untracked = {
        p.decode()
        for p in git(root, "ls-files", "--others", "--exclude-standard", "-z").split(
            b"\0"
        )
        if p
    }
    return sorted(p for p in unstaged | untracked if p not in excluded and _input(p))


def refresh(result, *, root=ROOT, check=False, hook=False):
    """Only allowlisted outputs may be written/staged; never stage source changes."""
    root = Path(root)
    for name in result:
        target = (root / name).resolve()
        if Path(name).is_absolute() or not target.is_relative_to(root.resolve()):
            raise ValueError("Generated output must stay inside the repository")
    if hook:
        unstaged = {
            p.decode() for p in git(root, "diff", "--name-only", "-z").split(b"\0") if p
        }
        untracked = {
            p.decode()
            for p in git(
                root, "ls-files", "--others", "--exclude-standard", "-z"
            ).split(b"\0")
            if p
        }
        pending = pending_inputs(root, result)
        if pending:
            raise ValueError(
                "Stage generation inputs first (partial commits are not generated): "
                + ", ".join(pending)
            )
        overwritten = [
            name
            for name, text in result.items()
            if name in unstaged | untracked
            and (root / name).exists()
            and (root / name).read_text(encoding="utf-8") != text
        ]
        if overwritten:
            raise ValueError(
                "Unstaged generated edits would be overwritten. Review them or run python -m scripts.generate_docs explicitly: "
                + ", ".join(overwritten)
            )
    write_outputs({root / name: text for name, text in result.items()}, check=check)
    if hook:
        subprocess.run(["git", "-C", str(root), "add", "--", *result], check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--hook", action="store_true")
    args = parser.parse_args(argv)
    try:
        # Reject unstaged source before importing application code for generation.
        if args.hook:
            pending = pending_inputs(ROOT, {"examples/apps/purchase/interfaces.py"})
            if pending:
                raise ValueError(
                    "Stage generation inputs first: " + ", ".join(sorted(pending))
                )
        result = outputs()
        refresh(result, check=args.check, hook=args.hook)
    except Exception as exc:
        print(f"Document generation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Generated documents: {len(result)} files "
        + (
            "checked"
            if args.check
            else "updated and staged"
            if args.hook
            else "updated"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
