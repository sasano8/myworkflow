"""Inspect emitted dataclasses independently of the generator's source template."""
from dataclasses import fields, is_dataclass
from typing import get_type_hints
from myworkflow.results import PipelineResult


def check_interfaces(expected_business, module):
    errors = []
    expected_names = set()
    for identity, pipeline in expected_business['pipelines'].items():
        for direction, references in [('Request', pipeline['inputs']), ('Response', ())]:
            name = pipeline['request_interface' if direction == 'Request' else 'response_interface']
            expected_names.add(name)
            def expected_type(artifact):
                if artifact.get('value_object'):
                    return expected_business['value_objects'][artifact['value_object']]['python_type']
                return artifact['type']
            expected = [(expected_business['artifacts'][r]['key'], expected_type(expected_business['artifacts'][r])) for r in references]
            if direction == 'Response':
                expected = [('code', 'int'), ('messages', 'tuple')]
            cls = getattr(module, name, None)
            actual = None
            schema_errors = []
            if isinstance(cls, type) and is_dataclass(cls):
                hints = get_type_hints(cls)
                def actual_type(name):
                    typ = hints.get(name)
                    if any(key == name and ':' in value for key, value in expected):
                        return f'{typ.__module__}:{typ.__qualname__}' if isinstance(typ, type) else str(typ)
                    return getattr(typ, '__name__', str(typ))
                actual = [(f.name, actual_type(f.name)) for f in fields(cls)]
                for reference in references:
                    artifact = expected_business['artifacts'][reference]
                    if artifact.get('value_object'):
                        definition = expected_business['value_objects'][artifact['value_object']]
                        model = hints.get(artifact['key'])
                        schema = model.model_json_schema(by_alias=False) if hasattr(model, 'model_json_schema') else None
                        if schema != definition['schema']:
                            schema_errors.append(artifact['value_object'])
            if actual != expected or schema_errors or (direction == 'Response' and cls is not PipelineResult):
                errors.append({'class': name, 'expected': expected, 'actual': actual,
                               **({'schema_errors': schema_errors} if schema_errors else {})})
    extras = sorted(name for name, cls in vars(module).items() if isinstance(cls, type) and is_dataclass(cls) and name not in expected_names and not (name == '_PipelineResult' and cls is PipelineResult))
    return {'expected_classes': len(expected_names), 'matched_classes': len(expected_names) - len(errors),
            'coverage': (len(expected_names) - len(errors)) / len(expected_names) if expected_names else 1.0,
            'errors': errors, 'unexpected_classes': extras, 'passed': not errors and not extras}
