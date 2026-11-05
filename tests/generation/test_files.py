"""generation behavior and invariants."""

from pathlib import Path
import tempfile
import pytest
from myworkflow.generation.files import write_outputs


def test_generation_rolls_back_all_outputs_if_replace_fails(monkeypatch):
    import os

    with tempfile.TemporaryDirectory() as directory:
        a, b = Path(directory) / "a", Path(directory) / "b"
        a.write_text("old-a")
        b.write_text("old-b")
        replace = os.replace

        def fail_second(src, dst):
            if dst == b:
                raise OSError("disk error")
            return replace(src, dst)

        with monkeypatch.context() as patcher:
            patcher.setattr("myworkflow.generation.files.os.replace", fail_second)
            with pytest.raises(OSError):
                write_outputs({a: "new-a", b: "new-b"})
        assert a.read_text() == "old-a"
        assert b.read_text() == "old-b"
        assert set(Path(directory).iterdir()) == {a, b}
