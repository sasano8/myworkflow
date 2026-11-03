from dataclasses import replace

import pytest

from examples.feature_demos.cron_reporting.contract import CATALOG, SCHEDULE
from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.schedules import validate_schedules


@pytest.mark.parametrize('expression', ['0 6 * * *', '*/15 0-23 * * 1-5', '0,30 8,18 1-31 1-12 0,7'])
def test_numeric_unix_cron_fields(expression):
    validate_schedules((replace(SCHEDULE, expression=expression),), CATALOG)


@pytest.mark.parametrize('expression', ['@daily', '* * * * * *', '60 6 * * *', '0 24 * * *',
                                      '0 6 0 * *', '0 6 * 13 *', '0 6 * * 8', '*/0 * * * *',
                                      '0 6 * * MON', '0 6 * * 5-1', '0,,30 6 * * *'])
def test_invalid_or_unsupported_cron_expressions_are_rejected(expression):
    with pytest.raises(ContractError):
        validate_schedules((replace(SCHEDULE, expression=expression),), CATALOG)


@pytest.mark.parametrize(('fields', 'message'), [
    ({'timezone': 'Unknown/Zone'}, 'timezone'),
    ({'workflow_id': 'w.unknown'}, 'unknown workflow'),
    ({'binding_id': 'b.unknown'}, 'binding does not belong'),
    ({'trigger_id': 't.unknown'}, 'trigger does not belong'),
])
def test_schedule_references_are_validated(fields, message):
    with pytest.raises(ContractError, match=message):
        validate_schedules((replace(SCHEDULE, **fields),), CATALOG)


def test_schedule_ids_are_unique():
    with pytest.raises(ContractError, match='unique'):
        validate_schedules((SCHEDULE, SCHEDULE), CATALOG)
