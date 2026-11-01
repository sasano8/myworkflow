"""Canonical symbolic purchase declarations. SPEC is a generated compatibility snapshot."""
from myworkflow import Artifact, Role
from myworkflow.declarations import bind, compile_workflows, trigger, workflow
from myworkflow.pipeline_declarations import Action, Mutex, Operation, PipelineDeclaration
from examples.apps.purchase import value_objects as vo

requester = Role('role.requester', '購買依頼部門の担当者', '申請者')
approver = Role('role.approver', '購買依頼部門の部門長', '承認者')
buyer = Role('role.buyer', '購買部の発注担当者', '発注担当者')
system = Role('role.system', '購買管理システム', 'システム')

application_id = Artifact('a.id', '購買申請ID', 'application_id', 'str', value_object=vo.application_id_type)
vendor = Artifact('a.vendor', '取引先', 'vendor', 'str', value_object=vo.vendor_type)
amount = Artifact('a.amount', '申請金額', 'amount', 'int', value_object=vo.amount_type)
application_status = Artifact('a.status', '申請状態', 'status', 'str')
quote_a = Artifact('a.quote-a', '見積書A', 'quote_a', 'str')
quote_b = Artifact('a.quote-b', '見積書B', 'quote_b', 'str')
attachment_receipt = Artifact('a.receipt', '添付登録結果', 'receipt', 'str')
decision = Artifact('a.decision', '承認判断', 'decision', 'bool')
eligible = Artifact('a.eligible', '発注可能', 'eligible', 'bool')
order_id = Artifact('a.order', '発注番号', 'order_id', 'str')

delete_quote_a = Operation('c.delete-a')
delete_quote_b = Operation('c.delete-b')

submit_lock = Mutex('s.submit-lock', '申請単位の排他', (application_id,))
save_application = Action(
    's.submit', '申請保存', '正の金額と取引先を確認し、申請者に紐づく承認待ちの申請を保存する。',
    reads=(application_id, vendor, amount),
    writes=(application_status,),
    uses=((application_id, 'DB作成'), (application_status, '保持')),
)
submit_application = PipelineDeclaration(
    'p.submit', '購買申請受付', (application_id, vendor, amount), (application_id, application_status),
    (submit_lock, save_application), reply=True,
)

upload_lock = Mutex('s.upload-lock', '申請単位の排他', (application_id,))
check_attachment = Action(
    's.check-upload', '添付可否確認', '申請者本人であり、申請が承認待ちであることを確認する。',
    reads=(application_id,),
)
save_quote_a = Action(
    's.put-a', '見積書A保存', '今回の実行専用キーで見積書Aを保存する。',
    reads=(application_id, quote_a),
    uses=((quote_a, '参照'),),
    compensate=delete_quote_a,
    attempts=2,
)
save_quote_b = Action(
    's.put-b', '見積書B保存', '見積書Bを保存し、両方の添付情報を申請に紐づける。',
    reads=(application_id, quote_b),
    writes=(attachment_receipt,),
    uses=((quote_b, '参照'), (attachment_receipt, 'DB作成')),
    compensate=delete_quote_b,
    attempts=2,
)
upload_quotes = PipelineDeclaration(
    'p.upload', '見積書2件登録', (application_id, quote_a, quote_b), (attachment_receipt,),
    (upload_lock, check_attachment, save_quote_a, save_quote_b), reply=True,
)

approval_lock = Mutex('s.approve-lock', '申請単位の排他', (application_id,))
check_approval = Action(
    's.check-approval', '承認対象確認', '承認待ちかつ申請者と承認者が別人であることを確認する。',
    reads=(application_id,),
)
approve_application = Action(
    's.approve', '承認', '承認済みに更新する。',
    reads=(application_id,),
    writes=(application_status,),
    uses=((application_status, 'DB更新'),),
    when=(decision, True),
)
reject_application = Action(
    's.reject', '却下', '却下済みに更新する。発注は行わない。',
    reads=(application_id,),
    writes=(application_status,),
    uses=((application_status, 'DB更新'),),
    when=(decision, False),
)
record_decision = PipelineDeclaration(
    'p.approve', '承認判断の反映', (application_id, decision), (application_status,),
    (approval_lock, check_approval, approve_application, reject_application), reply=True,
)

check_handoff = Action(
    's.dispatch', '引継ぎ条件確認', '承認済みの購買申請IDを次ワークフローへ引き継ぐ。',
    reads=(application_id,),
)
dispatch_order = PipelineDeclaration(
    'p.dispatch', '発注確定の起動', (application_id,), (application_id,),
    (check_handoff,), reply=True,
)

order_lock = Mutex('s.order-lock', '申請単位の排他', (application_id,))
check_eligibility = Action(
    's.eligibility', '発注条件照会', '承認済み、見積書2件あり、未発注であることを確認する。',
    reads=(application_id,),
    writes=(eligible,),
    uses=((eligible, '保持'),),
)
confirm_order = Action(
    's.confirm', '発注確定', '発注作成と申請の発注確定済みへの更新を同一DBトランザクションで行う。',
    reads=(application_id,),
    writes=(order_id,),
    uses=((order_id, 'DB作成'), (application_status, 'DB更新')),
    when=(eligible, True),
)
reject_order = Action(
    's.stop', '発注拒否', '発注条件を満たさなければエラーとして終了し、発注しない。',
    reads=(application_id,),
    when=(eligible, False),
)
confirm_purchase = PipelineDeclaration(
    'p.confirm', '発注確定', (application_id,), (),
    (order_lock, check_eligibility, confirm_order, reject_order), reply=False,
)

@workflow(id='w.execution', name='承認済み購買申請の発注確定')
class PurchaseExecution:
    confirmation_requested = trigger('t.confirm', '承認ワークフローから起動', system, ((application_id, 'id'),))
    confirm = bind('b.confirm', confirm_purchase, (confirmation_requested,), (('system', system),))

@workflow(id='w.attach', name='購買申請への見積書添付')
class PurchaseAttachment:
    attachment_received = trigger('t.upload', '申請者が見積書2件をアップロード', requester, ((application_id, 'id'), (quote_a, 'file_a'), (quote_b, 'file_b')))
    upload = bind('b.upload', upload_quotes, (attachment_received,), (('system', system),))

@workflow(id='w.approval', name='購買申請の受付・承認')
class PurchaseApproval:
    submission = trigger('t.submit', '申請者がFEで申請', requester, ((application_id, 'id'), (vendor, 'vendor'), (amount, 'amount')))
    submit = bind('b.submit', submit_application, (submission,), (('system', system),))
    approval_received = trigger('t.approve', '承認者がFEで承認または却下', approver, ((application_id, 'id'), (decision, 'decision')), wait='承認イベントを受信')
    approve = bind('b.approve', record_decision, (approval_received,), (('system', system),))
    scheduled = trigger('t.timer', '指定日時に到達', system, ((application_id, 'id'),), wait='承認済みかつ指定日時に到達')
    manual = trigger('t.manual', '発注担当者がFEで開始', buyer, ((application_id, 'application'),))
    dispatch = bind('b.dispatch', dispatch_order, (scheduled, manual), (('system', system),), next_workflow=PurchaseExecution)

compiled = compile_workflows(
    PurchaseApproval, PurchaseAttachment, PurchaseExecution,
    artifacts=(application_id, vendor, amount, application_status, quote_a, quote_b, attachment_receipt, decision, eligible, order_id),
    pipelines=(submit_application, upload_quotes, record_decision, dispatch_order, confirm_purchase),
    roles=(requester, approver, buyer, system),
)
program = compiled.program
# Export only: application code uses program; tests/importers may take an independent snapshot.
SPEC = program.spec
