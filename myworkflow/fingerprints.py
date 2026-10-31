"""Content fingerprints include newly added files without hand-maintained file lists."""
import hashlib
import json


def tree_fingerprint(root, sources):
    files = set()
    for source in sources:
        files.update([source] if source.is_file() else (p for p in source.rglob('*')
            if p.is_file() and p.suffix in {'.py', '.json', '.toml', '.feature'} and '__pycache__' not in p.parts))
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def contract_fingerprint(program):
    return hashlib.sha256(json.dumps(program.spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
