from contextlib import closing
from datetime import datetime, timezone
import sqlite3
import subprocess
import sys

import pytest

from examples.feature_demos.cron_reporting.application import run, target_date


def test_previous_business_date_uses_declared_timezone_and_handles_leap_days():
    assert target_date(datetime(2030, 4, 1, 16, tzinfo=timezone.utc)) == '2030-04-01'
    assert target_date(datetime(2032, 3, 1, 0, tzinfo=timezone.utc)) == '2032-02-29'
    with pytest.raises(ValueError, match='timezone'):
        target_date(datetime(2030, 4, 1))


def test_repeated_and_concurrent_invocations_do_not_duplicate_reports(tmp_path):
    path = tmp_path / 'reports.db'
    assert run(path, '2030-04-01').code == 0
    # Separate processes emulate overlapping cron invocations against one DB.
    args = [sys.executable, '-m', 'examples.feature_demos.cron_reporting',
            '--database', str(path), '--date', '2030-04-01']
    processes = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
    for process in processes:
        output, errors = process.communicate(timeout=20)
        assert process.returncode == 0, errors
        assert '2030-04-01の日次レポート' in output
    assert run(path, '2030-04-02').code == 0
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('SELECT business_date FROM reports ORDER BY business_date').fetchall() == [('2030-04-01',), ('2030-04-02',)]
        assert db.execute("SELECT count(*) FROM runs WHERE status='completed'").fetchone()[0] == 4


def test_invalid_business_date_does_not_write_a_database(tmp_path):
    path = tmp_path / 'reports.db'
    with pytest.raises(ValueError):
        run(path, '2030-02-30')
    assert not path.exists()
