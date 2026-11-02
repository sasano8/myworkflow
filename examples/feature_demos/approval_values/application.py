"""A declared transition enforces plain status updates and optimistic final commit."""
from pathlib import Path

from myworkflow import Artifact, Role, annotate
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
from myworkflow.storage.artifacts import ArtifactWrite
from myworkflow.compiler.declarations import bind, compile_workflows, state, transition, trigger, workflow
from myworkflow.executable import Context, Engine, Registry
from myworkflow.compiler.pipelines import Action, PipelineDeclaration
from myworkflow.runtime.transitions import GuardContext, TransitionRuntime

from examples.feature_demos.approval_values.value_objects import application_identifier, approval_application, purchase_amount, delivery_period

application_id = Artifact('a.guarded_id', '申請ID', 'application_id', 'str', value_object=application_identifier)
reviewer = Role('role.guarded_reviewer', '審査責任者', '承認者')
system = Role('role.guarded_system', '業務システム', 'システム')
@annotate(Action('s.guarded_approve', '承認変更の作成',
                 extensions={'ui': {'label': '承認する'}}))
def approve(ctx: Context) -> None:
    """申請者本人の承認を拒否し、承認者と承認済みの状態を変更予定に記録する。"""
    application = ctx.changes.subject
    ctx.changes.update(application, approved_by=ctx.actor, status=Approval.approved.id)
    ctx.add_message('承認変更を作成しました')


@annotate(PipelineDeclaration('p.guarded_approve', '申請承認', (application_id,), (), (approve,)))
def approval():
    """The compiler reads metadata without executing this function."""


def may_approve(ctx: GuardContext) -> bool:
    return ctx.application['owner'] != ctx.actor and ctx.application['amount'] > 0


@workflow(id='w.guarded_approval', name='トランジション契約に従う申請承認')
class Approval:
    waiting = state('state.guarded_waiting', '承認待ち', initial=True)
    approved = state('state.guarded_approved', '承認済み')
    requested = trigger('t.guarded_approve', '承認操作', reviewer, ((application_id, 'id'),))
    execute = bind('b.guarded_approve', approval, (requested,), (('system', system),))
    approve = transition('tr.guarded_approve', '承認', waiting, approved, execute, requested,
                         condition='申請者本人ではなく、金額が正である', guard=may_approve)


compiled = compile_workflows(Approval, artifacts=(application_id,),
                             value_objects=(application_identifier, purchase_amount, approval_application, delivery_period))
registry = Registry()


registry.register(approve)

def seed(coordinator, identity='example'):
    coordinator.prepare(f'seed:{identity}', (
        ArtifactWrite(f'application:{identity}', approval_application.normalize(
            {'owner': 'alice', 'amount': 100, 'status': Approval.waiting.id})),
    ))
    coordinator.commit(f'seed:{identity}')


def engine(coordinator, journal_path: Path, *, handlers=None):
    transitions = TransitionRuntime(compiled, compiled.graphs[0], coordinator,
                                    key=lambda values: f"application:{values['application_id']}",
                                    value_object=approval_application)
    return Engine(compiled.program, handlers or registry, None,
                  store=SQLiteExecutionStore(SQLiteDatabase(journal_path)), transitions=transitions)
