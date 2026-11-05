"""Insurance requirements: local IDs belong to the insurance catalog."""

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

request = Artifact("a.request", "保険申込", "request", "str")
process = Pipeline(
    "p.process",
    "保険申込の処理",
    (request.id,),
    (),
    (
        Step(
            "s.check",
            "申込内容の確認",
            "保険商品の申込内容と契約条件を照合する。",
            reads=(request.id,),
        ),
        Step(
            "s.calculate",
            "保険料の算定",
            "補償内容と契約期間を用いて保険料を算定する。",
            reads=(request.id,),
        ),
        Step(
            "s.prepare",
            "審査資料の作成",
            "保険申込の審査用資料を作成する。",
            reads=(request.id,),
        ),
    ),
)
requested = Trigger(
    "t.request",
    "保険申込の処理依頼",
    ((request.id, "request"),),
    actor_role_id=operator.id,
)
placement = Binding("b.process", process.id, (requested,), (("system", system.id),))
main = Workflow("w.main", "保険申込の業務", (placement,))
CATALOG = ContractCatalog(
    (request,),
    (process,),
    (main,),
    (operator, system),
    id="product.insurance",
    name="保険商品",
)
