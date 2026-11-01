"""Interface and unimplemented-handler generation."""
def class_name(identity):
    return ''.join(part.title() for part in identity.replace('.', '-').split('-'))


def interfaces_source(program):
    lines = ['"""Generated interfaces. Edit the contract, then regenerate."""',
             'from dataclasses import dataclass',
             'from myworkflow.results import PipelineResult as _PipelineResult', '']
    definitions = []
    for pipeline in program.plans.values():
        for identity in pipeline.inputs:
            definition = program.artifacts[identity].value_object
            if definition is not None and all(definition is not d for d in definitions):
                definitions.append(definition)
    import keyword
    for index, definition in enumerate(definitions):
        model = definition.model
        path = model.__module__ + '.' + model.__qualname__
        if model.__module__ == '__main__' or any(not p.isidentifier() or keyword.iskeyword(p) for p in path.split('.')):
            raise ValueError(f'{definition.id}: generated interfaces require an importable model class')
        lines.extend([f'import {model.__module__} as _ValueModule{index}',
                      f'_Value{index} = _ValueModule{index}.{model.__qualname__}', ''])
    for p in program.plans.values():
        name = class_name(p['id'])
        lines.extend(['@dataclass(frozen=True)', f'class {name}Request:'])
        lines.extend([f'    {program.artifacts[a]["key"]}: {"_Value" + str(definitions.index(program.artifacts[a].value_object)) if program.artifacts[a].value_object else program.artifacts[a].type}' for a in p.inputs] or ['    pass'])
        lines.extend(['', f'{name}Response = _PipelineResult', ''])
    return '\n'.join(lines).rstrip() + '\n'


def skeleton_source(program):
    lines = ['"""Generated skeleton: copy into your implementation; never overwrite existing work."""',
             'from myworkflow.executable import Context, Registry', '', 'registry = Registry()', '']
    ids = {s['id'] for s in program.steps.values() if s['kind'] != 'lock'} | {s['compensate'] for s in program.steps.values() if s.get('compensate')}
    for identity in sorted(ids):
        lines.extend([f'@registry.implements({identity!r})', f'def {class_name(identity).lower()}(ctx: Context) -> None:',
                      f'    raise NotImplementedError({identity!r})', ''])
    return '\n'.join(lines).rstrip() + '\n'
