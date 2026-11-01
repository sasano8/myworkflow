"""Refresh current generated examples; reviewed requirements and test oracles are inputs."""
import argparse
from pathlib import Path
import subprocess
import sys

from myworkflow.generation import write_outputs

ROOT = Path(__file__).resolve().parents[1]


def outputs():
    from examples.purchase import contract, handlers
    from examples.purchase.build import BUILD as PURCHASE
    from examples.approval_values_build import BUILD as VALUES
    from examples.declarative_review import compiled, documentation
    from examples.purchase.acceptance.catalog import CONFIG as purchase_acceptance
    from examples.tickets.acceptance.catalog import CONFIG as ticket_acceptance
    from myworkflow.acceptance.rendering import render_business, render_cases
    from myworkflow.build import compile_outputs
    from myworkflow.flowchart import render_business_flow
    purchase = compile_outputs(PURCHASE, target='temporal')
    preview = compile_outputs(PURCHASE, target='kestra', workflows=('w.attach',))
    values = compile_outputs(VALUES, target='temporal')
    result = {
        'examples/purchase/interfaces.py': purchase['interfaces.py'],
        'examples/purchase/docs/requirements.md': contract.program.documentation(handlers.registry, details_link='../../../docs/execution-design.md'),
        'examples/purchase/docs/data-definitions.md': purchase['data-definitions.md'],
        'examples/purchase/docs/data-definitions.json': purchase['data-definitions.json'],
        'examples/purchase/docs/kestra-attachment.yaml': preview['manifest.yaml'],
        'examples/approval-values/docs/requirements.md': values['requirements.md'],
        'examples/approval-values/docs/data-definitions.md': values['data-definitions.md'],
        'examples/approval-values/docs/data-definitions.json': values['data-definitions.json'],
        'examples/declarative_review/docs/requirements.md': documentation(),
        'examples/declarative_review/docs/flow.md': render_business_flow(compiled.graphs[0], compiled.catalog),
    }
    for config in (purchase_acceptance, ticket_acceptance):
        cases = config.cases()
        directory = config.output_directory.relative_to(ROOT)
        result[str(directory / 'business.md')] = render_business(config.program, config.registry, cases, options=config.documents)
        result[str(directory / 'acceptance.md')] = render_cases(cases, config.definitions, options=config.documents)
    labels = {
        'requirements.md': '業務要件・型・実装対応',
        'business.md': '業務要件と受入条件の対応',
        'acceptance.md': '受入シナリオ',
        'data-definitions.md': 'データ定義（1項目1行）',
        'data-definitions.json': '機械可読のデータ定義・JSON Schema',
        'flow.md': '業務フロー図',
        'kestra-attachment.yaml': 'Kestra説明用プレビュー（配備不可）',
    }
    catalogs = {
        'examples/purchase/docs': '購買',
        'examples/approval-values/docs': '承認・バリューオブジェクト例',
        'examples/declarative_review/docs': '申請審査',
        'examples/tickets/docs': 'チケット発行',
    }
    for directory, name in catalogs.items():
        files = sorted(Path(file).name for file in result if str(Path(file).parent) == directory)
        lines = [f'# {name}の業務契約カタログ', '',
                 'このディレクトリは宣言コードから自動生成する。変更は元のコード・受入シナリオへ反映する。', '',
                 '| ドキュメント | 内容 |', '| --- | --- |']
        lines.extend(f'| [{file}]({file}) | {labels[file]} |' for file in files)
        result[directory + '/README.md'] = '\n'.join(lines) + '\n'
    return result


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def _input(path):
    return (path == 'pyproject.toml' or path.startswith('.githooks/') or
            (path.startswith(('myworkflow/', 'examples/', 'scripts/')) and
             Path(path).suffix in ('.py', '.feature', '.toml', '.sh')))


def pending_inputs(root, excluded):
    unstaged = {p.decode() for p in git(root, 'diff', '--name-only', '-z').split(b'\0') if p}
    untracked = {p.decode() for p in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if p}
    return sorted(p for p in unstaged | untracked if p not in excluded and _input(p))


def refresh(result, *, root=ROOT, check=False, hook=False):
    """Only allowlisted outputs may be written/staged; never stage source changes."""
    root = Path(root)
    for name in result:
        target = (root / name).resolve()
        if Path(name).is_absolute() or not target.is_relative_to(root.resolve()):
            raise ValueError('Generated output must stay inside the repository')
    if hook:
        unstaged = {p.decode() for p in git(root, 'diff', '--name-only', '-z').split(b'\0') if p}
        untracked = {p.decode() for p in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if p}
        pending = pending_inputs(root, result)
        if pending:
            raise ValueError('Stage generation inputs first (partial commits are not generated): ' + ', '.join(pending))
        overwritten = [name for name, text in result.items() if name in unstaged | untracked
                       and (root / name).exists() and (root / name).read_text(encoding='utf-8') != text]
        if overwritten:
            raise ValueError('Unstaged generated edits would be overwritten. Review them or run python -m scripts.generate_docs explicitly: ' + ', '.join(overwritten))
    write_outputs({root / name: text for name, text in result.items()}, check=check)
    if hook:
        subprocess.run(['git', '-C', str(root), 'add', '--', *result], check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--hook', action='store_true')
    args = parser.parse_args(argv)
    try:
        # Reject unstaged source before importing application code for generation.
        if args.hook:
            pending = pending_inputs(ROOT, {'examples/purchase/interfaces.py'})
            if pending:
                raise ValueError('Stage generation inputs first: ' + ', '.join(sorted(pending)))
        result = outputs()
        refresh(result, check=args.check, hook=args.hook)
    except Exception as exc:
        print(f'Document generation failed: {exc}', file=sys.stderr)
        return 1
    print(f'Generated documents: {len(result)} files ' + ('checked' if args.check else 'updated and staged' if args.hook else 'updated'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
