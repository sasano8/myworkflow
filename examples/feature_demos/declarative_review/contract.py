"""Named declarations: inspect approval/revision cycles without executing handlers.

Run: python -m examples.feature_demos.declarative_review
This example declares contracts only; it does not persist a review or its state.
"""
from myworkflow import Artifact, Pipeline, Role, Step, Use
from myworkflow.declarations import bind, compile_workflows, state, transition, trigger, workflow
from myworkflow.state_graph import render_state_graph
from myworkflow.flowchart import render_business_flow

application_id = Artifact('a.review_id', '申請ID', 'application_id', 'str')
decision = Artifact('a.review_decision', '審査判断', 'decision', 'str')
requester = Role('role.requester', '申請部門の担当者', '申請者')
approver = Role('role.approver', '申請内容を審査する責任者', '承認者')
system = Role('role.system', '業務システム', 'システム')

submit_application = Pipeline('p.review_submit', '申請内容の受付', (application_id.id,), (application_id.id,), (
    Step('s.review_submit', '申請の記録', '申請内容を受け付ける。',
         uses=(Use(application_id.id, '参照'),), reads=(application_id.id,)),
))
record_review = Pipeline('p.review_record', '審査結果の反映', (application_id.id, decision.id), (application_id.id,), (
    Step('s.review_record', '審査操作の記録', '対象申請に対する審査判断（承認・差戻し・却下）を記録する。',
         uses=(Use(application_id.id, '参照'), Use(decision.id, '参照')), reads=(application_id.id, decision.id)),
))


@workflow(id='w.review', name='申請内容の審査と再申請')
class ApplicationReview:
    draft = state('state.review_draft', '未申請', initial=True)
    pending = state('state.review_pending', '承認待ち')
    revising = state('state.review_revising', '修正待ち')
    approved = state('state.review_approved', '承認済み')
    rejected = state('state.review_rejected', '却下済み')

    submission = trigger('t.review_submit', '申請操作', requester, ((application_id, 'id'),))
    approval = trigger('t.review_approve', '承認操作', approver, ((application_id, 'id'), (decision, 'decision')))
    revision = trigger('t.review_return', '差戻し操作', approver, ((application_id, 'id'), (decision, 'decision')))
    rejection = trigger('t.review_reject', '却下操作', approver, ((application_id, 'id'), (decision, 'decision')))
    resubmission = trigger('t.review_resubmit', '再申請操作', requester, ((application_id, 'id'),))

    submit = bind('b.review_submit', submit_application, (submission,), (('system', system),))
    review = bind('b.review_record', record_review, (approval, revision, rejection), (('system', system),))
    resubmit = bind('b.review_resubmit', submit_application, (resubmission,), (('system', system),))

    submit_transition = transition('tr.review_submit', '申請', draft, pending, submit, submission)
    approve_transition = transition('tr.review_approve', '承認', pending, approved, review, approval,
                                    condition='判断が承認で、承認権限があり、申請者本人ではない')
    return_transition = transition('tr.review_return', '差戻し', pending, revising, review, revision, condition='判断が差戻し')
    resubmit_transition = transition('tr.review_resubmit', '再申請', revising, pending, resubmit, resubmission)
    reject_transition = transition('tr.review_reject', '却下', pending, rejected, review, rejection, condition='判断が却下')


compiled = compile_workflows(ApplicationReview, artifacts=(application_id, decision))
program = compiled.program


def documentation():
    return (program.documentation() + '\n' + render_business_flow(compiled.graphs[0], compiled.catalog)
            + '\n' + render_state_graph(compiled.graphs[0], compiled.catalog))
