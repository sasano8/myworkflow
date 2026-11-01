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


def _display(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _type_label(schema):
    if '$ref' in schema:
        return schema['$ref'].rsplit('/', 1)[-1]
    for union in ('anyOf', 'oneOf'):
        if union in schema:
            return ' / '.join(_type_label(part) for part in schema[union])
    if schema.get('format') in ('date', 'date-time', 'uuid'):
        return {'date': '日付', 'date-time': '日時', 'uuid': 'UUID'}[schema['format']]
    kind = schema.get('type')
    if isinstance(kind, list):
        return ' / '.join(_type_label({'type': part}) for part in kind)
    if kind == 'array':
        return _type_label(schema.get('items', {})) + 'の配列'
    return {'string': '文字列', 'integer': '整数', 'number': '数値', 'boolean': '真偽値',
            'object': 'オブジェクト', 'null': 'null'}.get(kind, 'JSON参照')


def _constraints(schema):
    rules = []
    labels = {'minimum': '以上', 'exclusiveMinimum': 'より大きい', 'maximum': '以下', 'exclusiveMaximum': '未満'}
    for key, label in labels.items():
        if key in schema:
            rules.append(_display(schema[key]) + label)
    for key, label in (('minLength', '文字数の下限'), ('maxLength', '文字数の上限'),
                       ('minItems', '要素数の下限'), ('maxItems', '要素数の上限'),
                       ('pattern', '形式'), ('multipleOf', '倍数')):
        if key in schema:
            rules.append(label + '：' + _display(schema[key]))
    if schema.get('format') and schema['format'] not in ('date', 'date-time', 'uuid'):
        rules.append('形式：' + schema['format'])
    if 'enum' in schema:
        rules.append('選択肢：' + '、'.join(_display(v) for v in schema['enum']))
    if 'const' in schema:
        rules.append('固定値：' + _display(schema['const']))
    if schema.get('additionalProperties') is False:
        rules.append('未知の項目を拒否')
    if schema.get('uniqueItems'):
        rules.append('重複不可')
    for union in ('anyOf', 'oneOf', 'allOf'):
        if union in schema:
            branches = [part for part in schema[union] if part.get('type') != 'null']
            if len(branches) > 1:
                relation = 'すべて' if union == 'allOf' else 'いずれか'
                rules.append(relation + '：' + '／'.join(_type_label(part) + '（' + _constraints(part) + '）' for part in branches))
            elif branches:
                rule = _constraints(branches[0])
                if rule != '—':
                    rules.append(rule)
    # This is a summary. Preserve less common schema conditions in the JSON output.
    covered = {'title', 'description', 'type', 'format', 'default', 'examples', '$defs', '$ref',
               'properties', 'required', 'items', 'additionalProperties', 'enum', 'const', 'uniqueItems',
               'anyOf', 'oneOf', 'allOf', *labels, 'minLength', 'maxLength', 'minItems', 'maxItems', 'pattern', 'multipleOf'}
    if set(schema) - covered or any(k in schema for k in ('oneOf', 'allOf')):
        rules.append('追加条件はJSON参照')
    return '／'.join(dict.fromkeys(rules)) or '—'


def _field_rows(schema):
    definitions = schema.get('$defs', {})
    def walk(field, path, required, active=()):
        reference = field.get('$ref')
        resolved = definitions.get(reference.rsplit('/', 1)[-1], {}) if reference else {}
        field = {**resolved, **field}
        cells = (path, _type_label(field), required, field.get('description', '—'), _constraints(field),
                 _display(field['default']) if 'default' in field else '—',
                 '、'.join(_display(v) for v in field.get('examples', ())) or '—')
        yield cells
        if reference and reference in active:
            return
        active = (*active, reference) if reference else active
        for name, child in field.get('properties', {}).items():
            condition = '親あり時に必須' if name in field.get('required', ()) else '任意'
            yield from walk(child, path + '.' + name, condition, active)
        if field.get('type') == 'array' and isinstance(field.get('items'), dict):
            yield from walk(field['items'], path + '[]', '要素ごと', active)
        for union in ('anyOf', 'oneOf', 'allOf'):
            for index, child in enumerate(field.get(union, ())):
                if '$ref' in child or 'properties' in child:
                    yield from walk(child, f'{path}(候補{index + 1})', '条件付き', active)
    if 'properties' in schema:
        for name, child in schema['properties'].items():
            yield from walk(child, name, '必須' if name in schema.get('required', ()) else '任意')
    else:
        yield from walk(schema, '(値全体)', '必須')


def render_data_definitions(catalog):
    document = data_definitions(catalog)
    lines = ['# データ定義', '', '| 項目 | 内容 |', '| --- | --- |',
             '| 用途 | バリューオブジェクトの意味・制約の概要 |',
             '| 詳細 | [機械可読の定義・完全なJSON Schema](data-definitions.json) |',
             '| 検証 | 入力と、型を結び付けた更新の確定時に検証。内部の全変数でのクラス利用や直接DB更新は保証しない |', '']
    def row(cells):
        return '| ' + ' | '.join(escape(c) for c in cells) + ' |'
    for definition in document['value_objects']:
        validators = '、'.join(v.get('model', '') + ('.' if v.get('model') else '') + v['name']
                              for v in definition['validators'])
        lines.extend([f'<a id="{definition["id"]}"></a>', f'## {escape(definition["name"])}', '',
                      '| 項目 | 内容 |', '| --- | --- |', row(('固定ID', definition['id'])),
                      row(('Python型', definition['python_type'])),
                      row(('説明', definition['description'] or '未記載')),
                      row(('全体の制約', _constraints(definition['schema']))),
                      row(('補足ルール', '\n'.join(definition['rules']) or '未記載')),
                      row(('独自検証', (validators + '。意味は補足ルールと受入テストで確認。JSON Schemaだけでは全条件を表せない。')
                           if validators else 'なし'))])
        if definition.get('input_aliases'):
            lines.append(row(('入力の別名', '／'.join(f'{name} ← {_display(alias)}' for name, alias in definition['input_aliases'].items()))))
        lines.extend(['', '| 項目 | 型 | 必須 | 意味 | 制約 | 既定値 | 例 |', '| --- | --- | --- | --- | --- | --- | --- |'])
        lines.extend(row(cells) for cells in _field_rows(definition['schema']))
        lines.append('')
    lines.extend(['## アーティファクトとの対応', '', '| 固定ID | 名前 | バリューオブジェクト |', '| --- | --- | --- |'])
    for artifact in document['artifacts']:
        lines.append(row(artifact[k] for k in ('id', 'name', 'value_object')))
    return '\n'.join(lines).rstrip() + '\n'
