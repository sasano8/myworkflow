"""Interface and unimplemented-handler generation."""
def class_name(identity):
    return ''.join(part.title() for part in identity.replace('.', '-').split('-'))


def interfaces_source(program):
    lines = ['"""Generated interfaces. Edit the contract, then regenerate."""', 'from dataclasses import dataclass', '']
    for p in program.plans.values():
        for direction, ids in (("Request", p["inputs"]), ("Response", p["outputs"])):
            lines.extend(['@dataclass(frozen=True)', f'class {class_name(p["id"])}{direction}:'])
            lines.extend([f'    {program.artifacts[a]["key"]}: {program.artifacts[a]["type"]}' for a in ids] or ['    pass'])
            lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def skeleton_source(program):
    lines = ['"""Generated skeleton: copy into your implementation; never overwrite existing work."""',
             'from myworkflow.executable import Context, Registry', '', 'registry = Registry()', '']
    ids = {s['id'] for s in program.steps.values() if s['kind'] != 'lock'} | {s['compensate'] for s in program.steps.values() if s.get('compensate')}
    for identity in sorted(ids):
        lines.extend([f'@registry.implements({identity!r})', f'def {class_name(identity).lower()}(ctx: Context) -> None:',
                      f'    raise NotImplementedError({identity!r})', ''])
    return '\n'.join(lines).rstrip() + '\n'
