"""Public completion results retain status, messages and recovery failures, not artifacts."""
from copy import deepcopy

import pytest

from examples.tickets.contract import SPEC
from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
from myworkflow.executable import Context, Engine, Principal, Program, Registry
from myworkflow.errors import BusinessError, ExecutionFailed, PipelineError, RetryableError
from myworkflow.locking import InProcessLockProvider
from myworkflow.results import Message, PipelineResult


@pytest.fixture
def make_engine(tmp_path):
    def create(handler, *, reply=True, undo=None):
        spec = deepcopy(SPEC)
        spec['pipelines'][0]['reply'] = reply
        step = spec['pipelines'][0]['steps'][1]
        step['attempts'] = 2
        registry = Registry()
        @registry.implements('ticket.save')
        def perform(ctx: Context) -> None:
            handler(ctx)
        if undo:
            step['compensate'] = 'ticket.undo'
            @registry.implements('ticket.undo')
            def compensate(ctx: Context) -> None:
                undo(ctx)
        store = SQLiteExecutionStore(SQLiteDatabase(tmp_path / 'runs.db'))
        engine = Engine(Program(spec), registry, object(), locks=InProcessLockProvider(), store=store)
        return engine, store
    return create


def invoke(engine):
    return engine.invoke('ticket.binding', 'ticket.trigger', {'受付番号': 'T-001'},
                         Principal('operator', frozenset({'ticket.operator'})), run_id='one')


def test_success_returns_only_completion_with_all_message_levels(make_engine):
    def handler(ctx):
        ctx.values['receipt'] = 'artifact-only'
        for level in ('info', 'warning', 'error', 'critical'):
            ctx.add_message(level, level=level)
    engine, store = make_engine(handler)
    result = invoke(engine)
    assert result.code == 0 and result.ok
    assert [m.level for m in result.messages] == ['info', 'warning', 'error', 'critical']
    assert set(result.to_dict()) == {'code', 'messages'}
    assert 'artifact-only' not in str(result.to_dict())
    assert store.get('one')[0] == 'completed'


@pytest.mark.parametrize('exception', [BusinessError(42, '入力を確認してください', level='warning'),
                                       PipelineError(1001, 'サービスから拒否されました', level='error')])
def test_explicit_exception_code_and_messages_survive(make_engine, exception):
    def fail(ctx):
        ctx.add_message('検査を開始しました')
        raise exception
    engine, store = make_engine(fail)
    result = invoke(engine)
    assert result.code == exception.code and not result.ok
    assert result.messages == (Message('info', '検査を開始しました'), Message(exception.level, str(exception)))
    assert store.get('one')[0] == 'failed'


def test_unknown_exception_uses_1_and_strict_api_preserves_cause(make_engine):
    def fail(ctx):
        raise RuntimeError('unexpected')
    engine, store = make_engine(fail)
    result = invoke(engine)
    assert result == PipelineResult(1, (Message('error', 'unexpected'),))
    assert store.get('one')[0] == 'failed'
    with pytest.raises(ExecutionFailed) as caught:
        engine.run_or_raise('ticket.issue', {'number': 'T-001'}, actor='operator', run_id='strict')
    assert isinstance(caught.value.cause, RuntimeError)


def test_ingress_rejection_returns_result_without_executing(make_engine):
    calls = []
    engine, _ = make_engine(lambda ctx: calls.append('called'))
    denied = engine.invoke('ticket.binding', 'ticket.trigger', {'受付番号': 'T-001'},
                           Principal('intruder', frozenset()), run_id='denied')
    malformed = engine.invoke('ticket.binding', 'ticket.trigger', {},
                              Principal('operator', frozenset({'ticket.operator'})), run_id='invalid')
    assert denied.code == malformed.code == 1
    assert calls == []


def test_retry_is_not_converted_into_early_success(make_engine):
    attempts = []
    def handler(ctx):
        attempts.append('attempt')
        if len(attempts) == 1:
            raise RetryableError('temporary')
        ctx.values['receipt'] = 'done'
    engine, store = make_engine(handler)
    assert invoke(engine).code == 0
    assert len(attempts) == 2
    assert ['ticket.save', 'retry'] in store.get('one')[1]


def test_exhausted_retry_is_a_failed_result(make_engine):
    attempts = []
    def fail(ctx):
        attempts.append('attempt')
        raise RetryableError('unavailable')
    engine, store = make_engine(fail)
    assert invoke(engine).code == 1
    assert len(attempts) == 2
    assert store.get('one')[0] == 'failed'


def test_compensation_failure_overrides_business_rejection_with_critical(make_engine):
    def fail(ctx):
        raise BusinessError(42, '業務上の拒否', level='warning')
    def undo(ctx):
        raise OSError('cannot undo')
    engine, store = make_engine(fail, undo=undo)
    result = invoke(engine)
    assert result.code == 1
    assert result.messages[0] == Message('warning', '業務上の拒否')
    assert result.messages[-1].level == 'critical'
    assert 'cannot undo' in result.messages[-1].text
    assert store.get('one')[0] == 'manual-recovery'


def test_no_reply_still_returns_internal_status_and_checks_artifacts(make_engine):
    engine, _ = make_engine(lambda ctx: ctx.values.update(receipt='done'), reply=False)
    assert invoke(engine).code == 0


@pytest.mark.parametrize('construct', [
    lambda: PipelineResult(True), lambda: PipelineResult(-1), lambda: PipelineResult(messages=[]),
    lambda: Message('debug', 'unsupported'), lambda: Message('info', 1),
    lambda: PipelineError(0, 'failure'), lambda: PipelineError(True, 'failure'),
])
def test_invalid_result_contracts_are_rejected(construct):
    with pytest.raises(ValueError):
        construct()


def test_invalid_context_messages_are_a_failed_result(make_engine):
    def invalid(ctx):
        ctx.values['receipt'] = 'done'
        ctx.messages.append('not a Message')
    engine, store = make_engine(invalid)
    result = invoke(engine)
    assert result.code == 1
    assert result.messages[0].level == 'error'
    assert store.get('one')[0] == 'failed'


def test_journal_failure_is_critical_and_cannot_be_success(make_engine, monkeypatch):
    engine, store = make_engine(lambda ctx: ctx.values.update(receipt='done'))
    def unavailable(*args):
        raise OSError('journal unavailable')
    monkeypatch.setattr(store, 'record', unavailable)
    result = invoke(engine)
    assert result.code == 1
    assert any(m.level == 'critical' and 'journal unavailable' in m.text for m in result.messages)
