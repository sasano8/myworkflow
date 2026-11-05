"""Code-owned ticket declarations; SPEC is only a generated compatibility snapshot."""
from myworkflow import Artifact, Role, workflow
from myworkflow.compiler.declarations import bind, compile_workflows, trigger
from myworkflow.compiler.pipelines import Mutex, PipelineDeclaration, StepDeclaration

system = Role('role.system', 'チケット管理システム', 'システム')
operator = Role('ticket.operator', '窓口担当者', '受付担当')

number = Artifact('ticket.number', '受付番号', 'number')
receipt = Artifact('ticket.receipt', '発行結果', 'receipt')

number_lock = Mutex('ticket.lock', '受付番号の排他', (number,))
save_ticket = StepDeclaration(
    'ticket.save', 'チケット保存', '受付番号を重複なく登録し、発行結果を返す。',
    reads=(number,), writes=(receipt,),
    uses=((number, 'DB作成'), (receipt, '保持')),
)
issue_ticket = PipelineDeclaration(
    'ticket.issue', 'チケット発行', (number,), (receipt,), (number_lock, save_ticket),
)


@workflow(id='ticket.workflow', name='窓口でのチケット発行')
class TicketIssuance:
    requested = trigger('ticket.trigger', '担当者が発行を依頼', operator, ((number, '受付番号'),))
    issue = bind('ticket.binding', issue_ticket, (requested,), (('system', system),))


compiled = compile_workflows(TicketIssuance, artifacts=(number, receipt), roles=(system, operator))
program = compiled.program
SPEC = program.spec
