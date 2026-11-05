"""Cron declarations reference authorized workflow triggers; execution is external."""

from dataclasses import dataclass
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from myworkflow.contracts.errors import ContractError


@dataclass(frozen=True)
class CronSchedule:
    id: str
    name: str
    expression: str
    timezone: str
    workflow_id: str
    binding_id: str
    trigger_id: str


def validate_schedules(schedules, catalog):
    catalog.validate()
    if not isinstance(schedules, tuple) or any(
        not isinstance(s, CronSchedule) for s in schedules
    ):
        raise ContractError("schedules: expected a tuple of CronSchedule")
    workflows = {w.id: w for w in catalog.workflows}
    seen = set()
    for schedule in schedules:
        if (
            not isinstance(schedule.id, str)
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", schedule.id)
            or schedule.id in seen
        ):
            raise ContractError("Schedule IDs must be valid and unique")
        seen.add(schedule.id)
        if not isinstance(schedule.name, str) or not schedule.name.strip():
            raise ContractError(f"{schedule.id}: schedule name is required")
        try:
            ZoneInfo(schedule.timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
            raise ContractError(f"{schedule.id}: invalid timezone") from exc
        _validate_expression(schedule.expression)
        workflow = workflows.get(schedule.workflow_id)
        if workflow is None:
            raise ContractError(f"{schedule.id}: unknown workflow")
        binding = next(
            (b for b in workflow.bindings if b.id == schedule.binding_id), None
        )
        if binding is None:
            raise ContractError(f"{schedule.id}: binding does not belong to workflow")
        if not any(t.id == schedule.trigger_id for t in binding.triggers):
            raise ContractError(f"{schedule.id}: trigger does not belong to binding")


def _validate_expression(expression):
    """Five numeric UNIX fields: *, lists, ranges, and positive /steps."""
    fields = expression.split() if isinstance(expression, str) else []
    if len(fields) != 5:
        raise ContractError("cron requires five UNIX fields")
    for field, (low, high) in zip(
        fields, ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7)), strict=True
    ):
        for term in field.split(","):
            if not re.fullmatch(r"(\*|[0-9]+(-[0-9]+)?)(/[0-9]+)?", term):
                raise ContractError("Unsupported cron field: " + field)
            base, separator, stride = term.partition("/")
            if separator and int(stride) < 1:
                raise ContractError("Cron step must be positive")
            if base != "*":
                bounds = [int(n) for n in base.split("-")]
                if any(n < low or n > high for n in bounds) or bounds[0] > bounds[-1]:
                    raise ContractError("Cron field is out of range: " + field)
