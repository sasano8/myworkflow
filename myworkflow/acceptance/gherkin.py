import hashlib
import re
from myworkflow.acceptance.model import Case

def load_cases(paths, program, definitions):
    from gherkin.parser import Parser
    from gherkin.pickles.compiler import Compiler
    known = set(program.plans) | set(program.steps) | set(program.bindings)
    known |= {w.id for w in program.model.workflows}
    known |= set(program.artifacts) | {r.id for r in program.model.roles}
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
