"""Loan requirements reuse local IDs without referring to the insurance catalog."""

from myworkflow import (
    Artifact,
    Binding,
    ContractCatalog,
    Pipeline,
    Step,
    Trigger,
    Workflow,
)
from .shared import operator, system

request = Artifact("a.request", "融資申込", "request", "str")
process = Pipeline(
    "p.process",
    "融資申込の処理",
    (request.id,),
    (),
    (
        Step(
            "s.check",
            "申込内容の確認",
            "融資商品の申込内容と必要書類を確認する。",
            reads=(request.id,),
        ),
        Step(
            "s.calculate",
            "返済計画の計算",
            "金利と返済期間を用いて返済計画を計算する。",
            reads=(request.id,),
        ),
    ),
)
requested = Trigger(
    "t.request",
    "融資申込の処理依頼",
    ((request.id, "request"),),
    actor_role_id=operator.id,
)
placement = Binding("b.process", process.id, (requested,), (("system", system.id),))
main = Workflow("w.main", "融資申込の業務", (placement,))
CATALOG = ContractCatalog(
    (request,),
    (process,),
    (main,),
    (operator, system),
    id="product.loan",
    name="融資商品",
)
