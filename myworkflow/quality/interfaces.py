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
            expected = [(expected_business['artifacts'][r]['key'], expected_business['artifacts'][r]['type']) for r in references]
            if direction == 'Response':
                expected = [('code', 'int'), ('messages', 'tuple')]
            cls = getattr(module, name, None)
            actual = None
            if isinstance(cls, type) and is_dataclass(cls):
                hints = get_type_hints(cls)
                actual = [(f.name, getattr(hints.get(f.name), '__name__', str(hints.get(f.name)))) for f in fields(cls)]
            if actual != expected or (direction == 'Response' and cls is not PipelineResult):
                errors.append({'class': name, 'expected': expected, 'actual': actual})
    extras = sorted(name for name, cls in vars(module).items() if isinstance(cls, type) and is_dataclass(cls) and name not in expected_names and not (name == '_PipelineResult' and cls is PipelineResult))
    return {'expected_classes': len(expected_names), 'matched_classes': len(expected_names) - len(errors),
            'coverage': (len(expected_names) - len(errors)) / len(expected_names) if expected_names else 1.0,
            'errors': errors, 'unexpected_classes': extras, 'passed': not errors and not extras}
