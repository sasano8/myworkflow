"""Named Pydantic contracts and their independent, deterministic data definitions."""
from dataclasses import dataclass
import json
import re
from typing import get_args

from pydantic import BaseModel, ConfigDict

from myworkflow.errors import ContractError
from myworkflow.markdown import escape

PRIMITIVES = {'str': str, 'int': int, 'bool': bool, 'float': float, 'dict': dict}


class ValueModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', strict=True, validate_default=True)


@dataclass(frozen=True)
class ValueObject:
    id: str
    name: str
    model: type[BaseModel]
    description: str = ''
    rules: tuple[str, ...] = ()

    def check(self):
        if not isinstance(self.id, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', self.id):
            raise ContractError('Value object requires a valid stable ID')
        if not isinstance(self.name, str) or not self.name.strip() or not isinstance(self.description, str):
            raise ContractError(f'{self.id}: name and description must be text')
        if not isinstance(self.rules, tuple) or any(not isinstance(r, str) or not r.strip() for r in self.rules):
            raise ContractError(f'{self.id}: rules must be a tuple of nonempty explanations')
        if not isinstance(self.model, type) or not issubclass(self.model, BaseModel):
            raise ContractError(f'{self.id}: expected a Pydantic model class')
        if not self.model.model_config.get('frozen'):
            raise ContractError(f'{self.id}: model must be frozen')
        if not self.model.__pydantic_root_model__ and self.model.model_config.get('extra') != 'forbid':
            raise ContractError(f'{self.id}: model must forbid unknown fields')
        if not self.model.model_config.get('validate_default'):
            raise ContractError(f'{self.id}: model must validate defaults')
        try:
            json.dumps(self.model.model_json_schema(by_alias=False), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ContractError(f'{self.id}: model must have a JSON Schema ({exc})') from exc

    def normalize(self, value):
        """Accept JSON-shaped values or model instances; return validated JSON data."""
        try:
            if isinstance(value, BaseModel):
                if not isinstance(value, self.model):
                    raise ValueError('wrong Pydantic model')
                value = value.model_dump(mode='json', warnings='error')
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
            validated = self.model.model_validate_json(encoded, strict=True, by_name=True, by_alias=True)
            return validated.model_dump(mode='json', by_alias=False, warnings='error')
        except (TypeError, ValueError) as exc:
            raise ContractError(f'{self.id}: invalid value ({exc})') from exc

    def definition(self):
        self.check()
        validators = []
        visited = set()
        def inspect(annotation):
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                if annotation in visited:
                    return
                visited.add(annotation)
                for kind in ('field_validators', 'model_validators', 'validators', 'root_validators'):
                    for name, decorator in getattr(annotation.__pydantic_decorators__, kind).items():
                        validators.append({'name': name, 'kind': kind, 'fields': list(getattr(decorator.info, 'fields', ())),
                                           **({'model': f'{annotation.__module__}:{annotation.__qualname__}'}
                                              if annotation is not self.model else {})})
                for field in annotation.model_fields.values():
                    inspect(field.annotation)
            else:
                for child in get_args(annotation):
                    inspect(child)
        inspect(self.model)
        aliases = {name: (field.validation_alias if isinstance(field.validation_alias, str)
                          else field.validation_alias.convert_to_aliases())
                   for name, field in self.model.model_fields.items() if field.validation_alias is not None}
        return {'id': self.id, 'name': self.name, 'description': self.description,
                'python_type': f'{self.model.__module__}:{self.model.__qualname__}',
                'rules': list(self.rules), 'validators': validators,
                **({'input_aliases': aliases} if aliases else {}),
                'schema': self.model.model_json_schema(by_alias=False)}


def validate_definitions(definitions):
    if not isinstance(definitions, tuple) or any(not isinstance(d, ValueObject) for d in definitions):
        raise ContractError('value_objects must be a tuple of ValueObject declarations')
    ids = set()
    for definition in definitions:
        definition.check()
        if definition.id in ids:
            raise ContractError(f'{definition.id}: duplicate value object ID')
        ids.add(definition.id)


def data_definitions(catalog):
    validate_definitions(catalog.value_objects)
    return {'schema_version': 1, 'value_objects': [d.definition() for d in catalog.value_objects],
            'artifacts': [{'id': a.id, 'name': a.name, 'value_object': a.value_object.id}
                          for a in catalog.artifacts if a.value_object is not None]}


def data_definitions_source(catalog):
    return json.dumps(data_definitions(catalog), ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def render_data_definitions(catalog):
    document = data_definitions(catalog)
    lines = ['# データ定義', '',
             'Pythonのバリューオブジェクトから生成。業務要件の概要とは別に、値の意味と制約を示す。', '']
    for definition in document['value_objects']:
        lines.extend([f'<a id="{definition["id"]}"></a>', f'## {escape(definition["name"])}', '',
                      f'固定ID：{escape(definition["id"])}。Python型：{escape(definition["python_type"])}。', '',
                      escape(definition['description']) or '説明未記載。', '',
                      '| 項目 | 必須 | 説明 | 定義・制約・例 |', '| --- | --- | --- | --- |'])
        schema = definition['schema']
        properties = schema.get('properties', {'(値全体)': schema})
        required = schema.get('required', [])
        for name, field in properties.items():
            detail = {k: v for k, v in field.items() if k not in ('title', 'description')}
            cells = (name, '必須' if name in required or name == '(値全体)' else '任意',
                     field.get('description', '—'), json.dumps(detail, ensure_ascii=False, sort_keys=True))
            lines.append('| ' + ' | '.join(escape(c) for c in cells) + ' |')
        if definition.get('input_aliases'):
            lines.extend(['', '入力の別名：' + escape(json.dumps(definition['input_aliases'], ensure_ascii=False)) + '。表とSchemaは正規の項目名を使う。'])
        lines.extend(['', '### 補足ルール', ''])
        lines.extend('- ' + escape(rule) for rule in definition['rules'])
        if not definition['rules']:
            lines.append('補足未記載。')
        if definition['validators']:
            lines.extend(['', '独自検証：' + '、'.join(escape(v['name']) for v in definition['validators']) +
                          '。検証の意味は補足ルールと受入テストで確認する。JSON Schemaだけでは全条件を表せない。'])
        lines.extend(['', '### 完全なJSON Schema', '', '```json',
                      # Escape HTML-sensitive characters and backticks inside fenced JSON.
                      json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True).replace('`', '\\u0060').replace('<', '\\u003c'),
                      '```', ''])
    lines.extend(['## アーティファクトとの対応', '', '| 固定ID | 名前 | バリューオブジェクト |', '| --- | --- | --- |'])
    for artifact in document['artifacts']:
        lines.append('| ' + ' | '.join(escape(artifact[k]) for k in ('id', 'name', 'value_object')) + ' |')
    lines.extend(['', '入力と宣言された更新の確定時に検証する。内部の全変数でこのクラスを使うことや、直接DB更新の検証は保証しない。', ''])
    return '\n'.join(lines)
