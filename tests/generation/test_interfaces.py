"""Value-object generation behavior."""
from types import ModuleType
from typing import get_type_hints
from pydantic import Field
from examples.feature_demos.approval_values import application as sample
from examples.feature_demos.approval_values.value_objects import ApplicationId
from myworkflow.generation.interfaces import interfaces_source
from myworkflow.executable import Engine
from myworkflow.generation.business import export_business
from myworkflow.quality.interfaces import check_interfaces

def test_generated_request_references_the_original_model_class():
    module = ModuleType('generated_value_interfaces')
    exec(interfaces_source(sample.compiled.program), module.__dict__)
    assert get_type_hints(module.PGuarded_ApproveRequest)['application_id'] is ApplicationId
    assert check_interfaces(export_business(sample.compiled.program), module)['passed']
    Engine(sample.compiled.program, sample.registry, None, module,
           store=type('Journal', (), {'begin': lambda *a: None, 'record': lambda *a: None})())



def test_interface_inspection_detects_schema_drift_even_with_same_python_name():
    from pydantic import create_model
    from typing import Annotated
    module = ModuleType('generated_value_interfaces')
    exec(interfaces_source(sample.compiled.program), module.__dict__)
    changed = create_model('ApplicationId', __base__=ApplicationId,
                           root=(Annotated[str, Field(pattern='^DIFFERENT$')], ...))
    changed.__module__ = ApplicationId.__module__
    changed.__qualname__ = ApplicationId.__qualname__
    module.PGuarded_ApproveRequest.__annotations__['application_id'] = changed
    report = check_interfaces(export_business(sample.compiled.program), module)
    assert not report['passed']
    assert report['errors'][0]['schema_errors'] == ['vo.application_id']
