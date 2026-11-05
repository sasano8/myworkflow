"""Named Pydantic contracts and their independent, deterministic data definitions."""

from myworkflow.contracts.annotations import Extensible, extension_fields
from dataclasses import dataclass
import json
import re
from typing import get_args

from pydantic import BaseModel, ConfigDict

from myworkflow.contracts.errors import ContractError

PRIMITIVES = {"str": str, "int": int, "bool": bool, "float": float, "dict": dict}


class ValueModel(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


@dataclass(frozen=True)
class ValueObject(Extensible):
    id: str
    name: str
    model: type[BaseModel]
    description: str = ""
    rules: tuple[str, ...] = ()

    def check(self):
        if not isinstance(self.id, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_.-]*", self.id
        ):
            raise ContractError("Value object requires a valid stable ID")
        if (
            not isinstance(self.name, str)
            or not self.name.strip()
            or not isinstance(self.description, str)
        ):
            raise ContractError(f"{self.id}: name and description must be text")
        if not isinstance(self.rules, tuple) or any(
            not isinstance(r, str) or not r.strip() for r in self.rules
        ):
            raise ContractError(
                f"{self.id}: rules must be a tuple of nonempty explanations"
            )
        if not isinstance(self.model, type) or not issubclass(self.model, BaseModel):
            raise ContractError(f"{self.id}: expected a Pydantic model class")
        if not self.model.model_config.get("frozen"):
            raise ContractError(f"{self.id}: model must be frozen")
        if (
            not self.model.__pydantic_root_model__
            and self.model.model_config.get("extra") != "forbid"
        ):
            raise ContractError(f"{self.id}: model must forbid unknown fields")
        if not self.model.model_config.get("validate_default"):
            raise ContractError(f"{self.id}: model must validate defaults")
        try:
            json.dumps(self.model.model_json_schema(by_alias=False), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ContractError(
                f"{self.id}: model must have a JSON Schema ({exc})"
            ) from exc

    def normalize(self, value):
        """Accept JSON-shaped values or model instances; return validated JSON data."""
        try:
            if isinstance(value, BaseModel):
                if not isinstance(value, self.model):
                    raise ValueError("wrong Pydantic model")
                value = value.model_dump(mode="json", warnings="error")
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
            validated = self.model.model_validate_json(
                encoded, strict=True, by_name=True, by_alias=True
            )
            return validated.model_dump(mode="json", by_alias=False, warnings="error")
        except (TypeError, ValueError) as exc:
            raise ContractError(f"{self.id}: invalid value ({exc})") from exc

    def definition(self, *, extension_encoder=None):
        self.check()
        validators = []
        visited = set()

        def inspect(annotation):
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                if annotation in visited:
                    return
                visited.add(annotation)
                for kind in (
                    "field_validators",
                    "model_validators",
                    "validators",
                    "root_validators",
                ):
                    for name, decorator in getattr(
                        annotation.__pydantic_decorators__, kind
                    ).items():
                        validators.append(
                            {
                                "name": name,
                                "kind": kind,
                                "fields": list(getattr(decorator.info, "fields", ())),
                                **(
                                    {
                                        "model": f"{annotation.__module__}:{annotation.__qualname__}"
                                    }
                                    if annotation is not self.model
                                    else {}
                                ),
                            }
                        )
                for field in annotation.model_fields.values():
                    inspect(field.annotation)
            else:
                for child in get_args(annotation):
                    inspect(child)

        inspect(self.model)
        aliases = {
            name: (
                field.validation_alias
                if isinstance(field.validation_alias, str)
                else field.validation_alias.convert_to_aliases()
            )
            for name, field in self.model.model_fields.items()
            if field.validation_alias is not None
        }
        return {
            **extension_fields(self, extension_encoder),
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "python_type": f"{self.model.__module__}:{self.model.__qualname__}",
            "rules": list(self.rules),
            "validators": validators,
            **({"input_aliases": aliases} if aliases else {}),
            "schema": self.model.model_json_schema(by_alias=False),
        }


def validate_definitions(definitions):
    if not isinstance(definitions, tuple) or any(
        not isinstance(d, ValueObject) for d in definitions
    ):
        raise ContractError("value_objects must be a tuple of ValueObject declarations")
    ids = set()
    for definition in definitions:
        definition.check()
        if definition.id in ids:
            raise ContractError(f"{definition.id}: duplicate value object ID")
        ids.add(definition.id)
