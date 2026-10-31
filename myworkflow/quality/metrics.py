"""Exact structural measures and explicitly curated source-requirement evidence."""
from collections import Counter
import hashlib


def flatten(value, path=''):
    if isinstance(value, dict) and value:
        result = {}
        for key, item in value.items():
            part = str(key).replace('~', '~0').replace('/', '~1')
            result.update(flatten(item, path + '/' + part))
        return result
    if isinstance(value, list) and value:
        result = {}
        for index, item in enumerate(value):
            result.update(flatten(item, path + '/' + str(index)))
        return result
    return {path: value}


def same(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def compare(expected, actual):
    wanted, observed = flatten(expected), flatten(actual)
    matching = sorted(k for k in wanted.keys() & observed.keys() if same(wanted[k], observed[k]))
    missing = [{'path': k, 'expected': wanted[k]} for k in sorted(wanted.keys() - observed.keys())]
    unexpected = [{'path': k, 'actual': observed[k]} for k in sorted(observed.keys() - wanted.keys())]
    mismatched = [{'path': k, 'expected': wanted[k], 'actual': observed[k]}
                  for k in sorted(wanted.keys() & observed.keys()) if not same(wanted[k], observed[k])]
    per_section = {}
    for section in sorted({p.split('/')[1] for p in wanted if p.startswith('/')}):
        keys = [k for k in wanted if k.startswith('/' + section + '/') or k == '/' + section]
        per_section[section] = {'expected': len(keys), 'matched': sum(k in matching for k in keys)}
    return {'expected_facts': len(wanted), 'actual_facts': len(observed), 'matched_facts': len(matching),
        'recall': len(matching) / len(wanted) if wanted else 1.0,
        'precision': len(matching) / len(observed) if observed else (1.0 if not wanted else 0.0),
        'exact_match': not (missing or unexpected or mismatched),
        'missing': missing, 'unexpected': unexpected, 'mismatched': mismatched, 'sections': per_section}


def pointer(document, path):
    value = document
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def source_coverage(source, corpus, actual):
    if type(corpus.get('schema_version')) is not int or corpus.get('schema_version') != 1 or not corpus.get('units'):
        raise ValueError('A nonempty reviewed source inventory is required')
    if hashlib.sha256(source.encode()).hexdigest() != corpus.get('source_sha256'):
        raise ValueError('Source changed: review the requirement inventory before scoring')
    scope = corpus['scope']
    start = source.index(scope['start']) + len(scope['start'])
    end = source.index(scope['end'], start)
    scoped = source[start:end]
    annotated = set()
    identities, results = set(), []
    for unit in corpus['units']:
        identity = unit['id']
        if identity in identities or not unit.get('quote') or unit['quote'] not in source:
            raise ValueError(f'{identity}: duplicate unit or invalid source quotation')
        identities.add(identity)
        position = scoped.find(unit['quote'])
        if position < 0:
            raise ValueError(f'{identity}: quotation is outside the reviewed requirement scope')
        annotated.update(range(position, position + len(unit['quote'])))
        checks = unit.get('checks', [])
        failures = []
        for check in checks:
            if check.get('level') not in ('structured', 'description') or check.get('operator', 'equals') not in ('equals', 'contains'):
                raise ValueError(f'{identity}: invalid evidence classification')
            if not isinstance(check.get('path'), str) or not check['path'].startswith('/'):
                raise ValueError(f'{identity}: evidence needs an absolute JSON pointer')
            if check.get('operator') == 'contains' and (not isinstance(check.get('expected'), str) or not check['expected'].strip()):
                raise ValueError(f'{identity}: description evidence cannot be empty')
            try:
                value = pointer(actual, check['path'])
                passed = (same(value, check['expected']) if check.get('operator', 'equals') == 'equals'
                          else isinstance(value, str) and isinstance(check['expected'], str) and check['expected'] in value)
            except (KeyError, IndexError, ValueError, TypeError):
                passed = False
                value = None
            if not passed:
                failures.append({'path': check['path'], 'expected': check['expected'], 'actual': value})
        if not checks:
            status = 'unrepresented'
        elif failures:
            status = 'missing'
        elif any(c['level'] == 'description' for c in checks):
            status = 'description_only'
        else:
            status = 'structured'
        results.append({'id': identity, 'quote': unit['quote'], 'status': status,
                        'evidence': checks, 'failures': failures, 'note': unit.get('note', '')})
    counts = Counter(r['status'] for r in results)
    covered = counts['structured'] + counts['description_only']
    gaps = sorted(r['id'] for r in results if r['status'] in ('missing', 'unrepresented'))
    approved = corpus.get('accepted_gaps', [])
    if len(approved) != len(set(approved)) or set(approved) - identities:
        raise ValueError('Accepted gaps must reference unique known requirement units')
    return {'source_inventory_coverage': sum(i in annotated for i, ch in enumerate(scoped) if not ch.isspace()) / sum(not ch.isspace() for ch in scoped),
            'total_units': len(results), 'counts': {k: counts[k] for k in ('structured', 'description_only', 'missing', 'unrepresented')},
            'documented_coverage': covered / len(results), 'structured_coverage': counts['structured'] / len(results),
            'gaps': gaps, 'new_gaps': sorted(set(gaps) - set(approved)), 'units': results}
