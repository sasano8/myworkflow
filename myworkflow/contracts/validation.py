"""Structural and semantic contract checks."""

import re

from myworkflow.contracts.models import Lock
from myworkflow.contracts.value_objects import validate_definitions


def validate_catalog(catalog):
    # Legacy standalone catalogs may omit identity; named catalogs require both fields.
    if catalog.id != "" or catalog.name != "":
        if (
            not isinstance(catalog.id, str)
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", catalog.id)
            or not isinstance(catalog.name, str)
            or not catalog.name.strip()
        ):
            raise ValueError("Catalog requires a valid ID and nonempty name")
    ids = [e.id for e in catalog.entities]
    if len(ids) != len(set(ids)) or any(
        not isinstance(i, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", i)
        for i in ids
    ):
        raise ValueError("IDs must be unique, nonempty and contain no slash")
    validate_definitions(catalog.value_objects)
    roles = {r.id for r in catalog.roles}
    if any(not r.name.strip() or not r.display_name.strip() for r in catalog.roles):
        raise ValueError("Role names must be nonempty")
    artifacts = {a.id for a in catalog.artifacts}
    pipelines = {p.id: p for p in catalog.pipelines}
    workflows = {w.id for w in catalog.workflows}
    for a in catalog.artifacts:
        if a.value_object is not None and not any(
            a.value_object is d for d in catalog.value_objects
        ):
            raise ValueError(f"{a.id}: value object must belong to catalog")
    for p in catalog.pipelines:
        if type(p.reply) is not bool:
            raise ValueError("Pipeline reply must be boolean")
        refs = list(p.inputs + p.outputs)
        for s in p.steps:
            if isinstance(s, Lock):
                if not s.keys:
                    raise ValueError("Lock requires context keys")
                refs.extend(s.keys)
            else:
                if not s.summary.strip():
                    raise ValueError("Step requires a business summary")
                for u in s.uses:
                    if u.operation not in {
                        "参照",
                        "保持",
                        "DB読取",
                        "DB作成",
                        "DB更新",
                        "送信",
                    }:
                        raise ValueError("Unknown artifact operation")
                    refs.append(u.artifact_id)
        if set(refs) - artifacts:
            raise ValueError("Unknown artifact reference")
    for w in catalog.workflows:
        placements = {b.id for b in w.bindings}
        for b in w.bindings:
            if b.pipeline_id not in pipelines:
                raise ValueError("Unknown pipeline reference")
            mapping = dict(b.role_mapping)
            required = {"system", *(s.actor for s in pipelines[b.pipeline_id].steps)}
            if len(mapping) != len(b.role_mapping) or set(mapping) != required:
                raise ValueError("Role mapping must cover pipeline role slots exactly")
            if set(mapping.values()) - roles:
                raise ValueError("Unknown mapped role")
            if not b.triggers:
                raise ValueError(f"{b.id}: no triggers")
            for t in b.triggers:
                if t.actor_role_id not in roles:
                    raise ValueError("Unknown trigger actor role")
                mapped = [target for target, source in t.input_mapping]
                if len(mapped) != len(set(mapped)) or set(mapped) != set(
                    pipelines[b.pipeline_id].inputs
                ):
                    raise ValueError(
                        "Input mapping must cover the pipeline contract exactly"
                    )
                sources = [source for _, source in t.input_mapping]
                if len(set(sources)) != len(sources):
                    raise ValueError(f"{t.id}: input sources must be unambiguous")
                if not t.name.strip() or any(
                    not source.strip() for _, source in t.input_mapping
                ):
                    raise ValueError("Trigger and input sources must be described")
                if t.after is not None and (
                    t.after not in placements or t.after == b.id
                ):
                    raise ValueError("Unknown or self-referencing preceding placement")
            if b.next_workflow_id is not None and b.next_workflow_id not in workflows:
                raise ValueError("Unknown next workflow reference")
