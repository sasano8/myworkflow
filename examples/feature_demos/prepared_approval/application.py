"""A pipeline prepares data/state artifacts and commits them in one local transaction."""
from dataclasses import dataclass
import json
from pathlib import Path

from myworkflow import Artifact, BusinessError, Pipeline, Role, Step
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
from myworkflow.storage.artifacts import ArtifactCoordinator, ArtifactWrite
from myworkflow.compiler.declarations import bind, compile_workflows, state, transition, trigger, workflow
from myworkflow.executable import Context, Engine, Registry

application_id = Artifact('a.staged_id', '申請ID', 'application_id', 'str')
application_version = Artifact('a.staged_version', '申請バージョン', 'application_version', 'int')
state_version = Artifact('a.staged_state_version', '状態バージョン', 'state_version', 'int')
proposed = Artifact('a.staged_changes', '確定予定の申請内容', 'proposed', 'str')
reviewer = Role('role.staged_reviewer', '申請の審査責任者', '承認者')
system = Role('role.staged_system', '業務システム', 'システム')

approval = Pipeline('p.staged_approval', '申請の承認確定', (application_id.id,), (), (
    Step('s.staged_read', '読込み・検証', '申請と状態を読み、承認可能であることを確認する。',
         reads=(application_id.id,), writes=(application_version.id, state_version.id, proposed.id)),
    Step('s.staged_prepare', '変更の準備', 'ジョブIDに申請と状態の変更を紐づけ、未確定で保存する。',
         reads=(application_id.id, application_version.id, state_version.id, proposed.id)),
    Step('s.staged_commit', '一括確定', 'バージョンの競合を検査し、申請と状態と確定結果をまとめて保存する。'),
))


@workflow(id='w.staged_approval', name='申請の準備と承認確定')
class PreparedApproval:
    pending = state('state.staged_pending', '承認待ち', initial=True)
    approved = state('state.staged_approved', '承認済み')
    requested = trigger('t.staged_approve', '承認操作', reviewer, ((application_id, 'id'),))
    execute = bind('b.staged_approve', approval, (requested,), (('system', system),))
    approve = transition('tr.staged_approve', '承認', pending, approved, execute, requested)


compiled = compile_workflows(PreparedApproval, artifacts=(application_id, application_version, state_version, proposed))
registry = Registry()


@dataclass
class ApprovalServices:
    coordinator: ArtifactCoordinator


@registry.implements('s.staged_read')
def read_and_validate(ctx: Context) -> None:
    coordinator = ctx.services.coordinator
    identity = ctx.values['application_id']
    application = coordinator.read(f'application:{identity}')
    status = coordinator.read(f'state:{identity}')
    if application is None or status is None or status.value != PreparedApproval.pending.id:
        raise BusinessError(10, '承認待ちの申請が必要です', level='warning')
    if application.value['owner'] == ctx.actor:
        raise BusinessError(11, '申請者本人は承認できません', level='warning')
    ctx.values['application_version'] = application.version
    ctx.values['state_version'] = status.version
    ctx.values['proposed'] = json.dumps({**application.value, 'approved_by': ctx.actor})


@registry.implements('s.staged_prepare')
def prepare(ctx: Context) -> None:
    identity = ctx.values['application_id']
    ctx.services.coordinator.prepare(ctx.run_id, (
        ArtifactWrite(f'application:{identity}', json.loads(ctx.values['proposed']), ctx.values['application_version']),
        ArtifactWrite(f'state:{identity}', PreparedApproval.approved.id, ctx.values['state_version']),
    ))


@registry.implements('s.staged_commit')
def commit(ctx: Context) -> None:
    ctx.services.coordinator.commit(ctx.run_id)
    ctx.add_message('申請と状態を確定しました')


def seed(coordinator: ArtifactCoordinator, identity='example'):
    coordinator.prepare(f'seed:{identity}', (
        ArtifactWrite(f'application:{identity}', {'owner': 'alice', 'amount': 100}),
        ArtifactWrite(f'state:{identity}', PreparedApproval.pending.id),
    ))
    coordinator.commit(f'seed:{identity}')


def engine(coordinator: ArtifactCoordinator, journal_path: Path):
    return Engine(compiled.program, registry, ApprovalServices(coordinator),
                  store=SQLiteExecutionStore(SQLiteDatabase(journal_path)))
