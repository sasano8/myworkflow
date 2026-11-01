"""Stage every output before replacing it; restore prior files on a write failure."""
import os
from pathlib import Path
import tempfile


def write_outputs(outputs, *, check=False, protected=()):
    outputs = {Path(p): text for p, text in outputs.items()}
    reserved = {Path(p).resolve() for p in protected}
    if any(p.resolve() in reserved for p in outputs):
        raise ValueError('Refusing to overwrite a handwritten source')
    stale = [p for p, text in outputs.items() if not p.exists() or p.read_text(encoding='utf-8') != text]
    if check:
        if stale:
            raise ValueError('Generated documents are stale: ' + ', '.join(map(str, stale)))
        return
    staged, previous = {}, {}
    replaced = []
    try:
        for path in stale:
            path.parent.mkdir(parents=True, exist_ok=True)
            previous[path] = path.read_bytes() if path.exists() else None
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
                temporary.write(outputs[path].encode('utf-8'))
                staged[path] = Path(temporary.name)
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
    except BaseException:
        for path in reversed(replaced):
            if previous[path] is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous[path])
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
