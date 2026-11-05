"""Human work declarations only: no mailbox integration, Engine or handlers."""

from myworkflow import (
    Artifact,
    Binding,
    ContractCatalog,
    Pipeline,
    Role,
    Step,
    Trigger,
    Use,
    Workflow,
)
from myworkflow.contracts.state_graph import State, StateGraph, Transition

DOCUMENTATION_NOTICE = (
    "人だけで行う業務の記述用サンプルです。申請者がメールを送り、受付担当者がメールソフトで受信・確認し、"
    "受付台帳へ記入します。メール受信・添付取得・台帳更新を自動実行するものではありません。"
    "実行ハンドラー・Engine・配備用のBuildConfigは定義しません。"
)
requester = Role(
    "role.mail_requester", "申請書をメールで送付する部門の担当者", "申請者"
)
clerk = Role(
    "role.mail_clerk", "申請メールと添付書類を確認し台帳へ記入する担当者", "受付担当者"
)
mail = Artifact("a.application_mail", "申請メール", "mail", "str")
form = Artifact("a.application_form", "添付申請書", "form", "str")
entry = Artifact("a.receipt_entry", "受付台帳の記入内容", "entry", "str")

receive = Step(
    "s.mail_receive",
    "申請書をメールで受信する",
    "受付担当者が共有メールボックスを開き、送信者と添付申請書を確認する。添付がなければ申請者へ再送を依頼する。",
    actor="clerk",
    reads=(mail.id,),
    writes=(form.id,),
    uses=(Use(mail.id, "参照"), Use(form.id, "保持")),
)
record = Step(
    "s.mail_record",
    "受付台帳へ記入する",
    "受付担当者が申請書を読み、申請者・件名・受信日時を受付台帳へ手作業で記入する。",
    actor="clerk",
    reads=(mail.id, form.id),
    writes=(entry.id,),
    uses=(Use(form.id, "参照"), Use(entry.id, "保持")),
)
receipt = Pipeline(
    "p.manual_receipt",
    "メールによる申請書受付（人手）",
    (mail.id,),
    (entry.id,),
    (receive, record),
    reply=False,
)
arrived = Trigger(
    "t.application_mail",
    "申請者から申請書添付メールが届く",
    ((mail.id, "共有メールボックスで受信した申請メール"),),
    actor_role_id=requester.id,
)
# The required system slot is also assigned to the clerk; no system role is declared.
placement = Binding(
    "b.manual_receipt",
    receipt.id,
    (arrived,),
    (("system", clerk.id), ("clerk", clerk.id)),
)
workflow = Workflow(
    "w.manual_receipt", "メールで届いた申請書の受付（人手）", (placement,)
)
catalog = ContractCatalog(
    (mail, form, entry), (receipt,), (workflow,), (requester, clerk)
)
received = State("state.mail_received", "申請メール受信")
registered = State("state.mail_registered", "受付台帳記入済み")
graph = StateGraph(
    workflow,
    received,
    (received, registered),
    (
        Transition(
            "tr.mail_register",
            "申請書確認と台帳記入",
            received,
            registered,
            placement,
            arrived,
            condition="添付申請書を確認し、受付台帳への記入を終えた",
        ),
    ),
)
