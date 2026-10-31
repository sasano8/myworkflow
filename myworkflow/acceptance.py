"""Optional Gherkin validation/documentation; business actions belong to the sample."""
from dataclasses import dataclass
from functools import wraps
import hashlib
import re


@dataclass(frozen=True)
class Definition:
    kind: str
    parser: object
    actor: str
    refs: tuple[str, ...]
    function: object


class Definitions:
    def __init__(self):
        self.items = []

    def step(self, kind, parser, *, actor, refs):
        from pytest_bdd import given, when, then
        if kind not in ('Context', 'Action', 'Outcome'):
            raise ValueError(f'Unknown step kind: {kind}')
        def register(fn):
            @wraps(fn)
            def invoke(*args, **kwargs):
                result = fn(*args, **kwargs)
                if kind == 'Outcome' and result is not True:
                    raise AssertionError(f'{fn.__name__}: expected True, got {result!r}')
                return result
            self.items.append(Definition(kind, parser, actor, tuple(refs), fn))
            decorator = {'Context': given, 'Action': when, 'Outcome': then}[kind]
            return decorator(parser, stacklevel=2)(invoke)
        return register

    def resolve(self, kind, text):
        matches = [d for d in self.items if d.kind == kind and d.parser.is_matching(text)]
        if len(matches) != 1:
            raise ValueError(f'Expected one implementation for {kind}: {text}; found {len(matches)}')
        return matches[0]


@dataclass(frozen=True)
class Case:
    id: str
    scenario_id: str
    name: str
    requirements: tuple[str, ...]
    steps: tuple[dict, ...]
    tags: tuple[str, ...]
    uri: str
    line: int
    source_hash: str


def load_cases(paths, program, definitions):
    from gherkin.parser import Parser
    from gherkin.pickles.compiler import Compiler
    known = set(program.plans) | set(program.steps) | set(program.bindings)
    known |= {w['id'] for w in program.spec['workflows']}
    known |= set(program.artifacts) | {r['id'] for r in program.spec['roles']}
    known |= {s['compensate'] for s in program.steps.values() if s.get('compensate')}
    cases, scenario_ids = [], set()
    for path in sorted(paths):
        source = path.read_text(encoding='utf-8')
        doc = Parser().parse(source)
        doc['uri'] = path.name
        row_ids = {}
        scenario_nodes = []
        def visit(children):
            for child in children:
                if 'rule' in child:
                    visit(child['rule']['children'])
                if 'scenario' in child:
                    scenario_nodes.append(child['scenario'])
        visit(doc['feature']['children'])
        for scenario in scenario_nodes:
            tags = [t['name'][1:] for t in doc['feature']['tags'] + scenario['tags']]
            identities = [t for t in tags if t.startswith('scenario.')]
            if len(identities) != 1 or identities[0] in scenario_ids:
                raise ValueError(f'{path.name}:{scenario["location"]["line"]}: scenario needs a unique scenario.ID tag')
            scenario_ids.add(identities[0])
            for example in scenario['examples']:
                headers = [c['value'] for c in example['tableHeader']['cells']]
                if 'case' not in headers:
                    raise ValueError('Scenario Outline requires a stable case column')
                for row in example['tableBody']:
                    row_ids[row['id']] = row['cells'][headers.index('case')]['value']
        compiled = Compiler().compile(doc)
        if not compiled:
            raise ValueError(f'{path.name}: no executable scenarios')
        for pickle in compiled:
            tags = tuple(t['name'][1:] for t in pickle['tags'])
            sid = next(t for t in tags if t.startswith('scenario.'))
            refs = tuple(t.removeprefix('req.') for t in tags if t.startswith('req.'))
            if not refs or set(refs) - known:
                raise ValueError(f'{sid}: missing or unknown requirement IDs: {refs}')
            variant = next((row_ids[i] for i in pickle['astNodeIds'] if i in row_ids), None)
            identity = sid + (f'.{variant}' if variant else '')
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', identity):
                raise ValueError(f'{sid}: invalid case ID {identity}')
            if not any(s['type'] == 'Outcome' for s in pickle['steps']):
                raise ValueError(f'{identity}: no acceptance assertions')
            for step in pickle['steps']:
                if step.get('argument'):
                    raise ValueError(f'{identity}: step tables/docstrings are not supported yet')
                definition = definitions.resolve(step['type'], step['text'])
                if set(definition.refs) - known:
                    raise ValueError(f'{identity}: implementation has unknown requirement references')
            cases.append(Case(identity, sid, pickle['name'], refs, tuple(pickle['steps']), tags,
                              path.name, pickle['location']['line'], hashlib.sha256(source.encode()).hexdigest()))
    if len({c.id for c in cases}) != len(cases):
        raise ValueError('Duplicate case IDs')
    return cases


def safe(value):
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('\n', '<br>')


def render_cases(cases, definitions):
    lines = ['# 購買フローの受入シナリオ', '', 'featureファイルが正本です。この文書は仕様であり、テスト成功の証明ではありません。', '']
    names = {'Context': '前提', 'Action': '操作', 'Outcome': '期待結果'}
    for case in cases:
        lines += [f'<a id="{case.id}"></a>', f'## {safe(case.name)}', '',
                  f'固定ID：`{case.id}`。基盤：' + ('Temporal' if 'temporal' in case.tags else 'ローカルEngine') + '。', '',
                  '対象：' + '、'.join(f'[{safe(r)}](business.md#{r})' for r in case.requirements), '',
                  f'正本：[ {safe(case.uri)}:{case.line} ](features/{case.uri}#L{case.line})', '',
                  '| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |', '| --- | --- | --- |']
        for s in case.steps:
            d = definitions.resolve(s['type'], s['text'])
            lines.append(f'| {names[s["type"]]} | {safe(d.actor)} | {safe(s["text"])} |')
        lines += ['', '<details>', '<summary>操作・検証の実装対応</summary>', '']
        for s in case.steps:
            d = definitions.resolve(s['type'], s['text'])
            lines.append(f'- {safe(s["text"])} → `{d.function.__module__}.{d.function.__name__}`')
        lines += ['', '</details>', '']
    return '\n'.join(lines).rstrip() + '\n'


def render_business(program, registry, cases):
    text = program.documentation(registry, details_link='../../../docs/execution-design.md') + '\n## 受入条件との対応\n\n'
    for identity in sorted({r for c in cases for r in c.requirements}):
        text += f'<a id="{identity}"></a>\n### {identity}\n\n'
        for case in cases:
            if identity in case.requirements:
                text += f'- [{safe(case.name)}](acceptance.md#{case.id})\n'
        text += '\n'
    return text.rstrip() + '\n'


def render_report(payload, cases, contract_hash, implementation_hash=None):
    results = {r['case_id']: r for r in payload.get('cases', [])}
    known = {c.id for c in cases}
    if set(results) - known:
        raise ValueError('Report references unknown cases')
    statuses = {'passed': '合格', 'failed': '失敗', 'skipped': 'スキップ', 'not-run': '未実行'}
    lines = ['# 購買フローの受入テスト結果', '',
             f"対象コミット：{safe(payload.get('commit') or '不明')}。未コミット変更：{safe(payload.get('working_tree_dirty'))}。",
             f"実行終了コード：{safe(payload.get('session_exitstatus'))}。", '',
             '定義が変わった結果は過去結果として表示します。仕様文書とは別の実行記録です。', '',
             '| ケースID | 業務契約 | 結果 |', '| --- | --- | --- |']
    for case in cases:
        result = results.get(case.id, {'status': 'not-run'})
        status = result['status']
        if status not in statuses:
            raise ValueError(f'Unknown result status: {status}')
        label = statuses[status]
        if status != 'not-run' and (result.get('source_sha256') != case.source_hash or payload.get('contract_sha256') != contract_hash or (implementation_hash is not None and payload.get('implementation_sha256') != implementation_hash)):
            label = f'過去結果（定義変更あり）：{label}'
        lines.append(f'| {case.id} | {safe("、".join(case.requirements))} | {label} |')
    return '\n'.join(lines) + '\n'
