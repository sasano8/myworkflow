"""Run the documented purchase flow without external services."""
from myworkflow.generation.documents import document_program
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from examples.apps.purchase import contract as c
from examples.apps.purchase.handlers import registry
from examples.apps.purchase import interfaces
from examples.apps.purchase.services import Services
from myworkflow.executable import Engine, Principal

program = c.program


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docs', action='store_true')
    args = parser.parse_args()
    if args.docs:
        print(document_program(program, registry, details_link="../../../../docs/execution-design.md"), end='')
        return
    with TemporaryDirectory() as directory:
        services = Services(Path(directory) / 'purchase.db')
        engine = Engine(program, registry, services, interfaces)
        applicant = Principal('alice', frozenset({c.requester.id}))
        approver = Principal('bob', frozenset({c.approver.id}))
        system = Principal('scheduler', frozenset({c.system.id}))
        print(engine.handler(c.PurchaseApproval.submit, c.PurchaseApproval.submission).handle({'id': 'purchase-001', 'vendor': 'サンプル商事', 'amount': 10000}, applicant, run_id='submit-001'))
        print(engine.handler(c.PurchaseAttachment.upload, c.PurchaseAttachment.attachment_received).handle({'id': 'purchase-001', 'file_a': '見積書A本文', 'file_b': '見積書B本文'}, applicant, run_id='upload-001'))
        print(engine.handler(c.PurchaseApproval.approve, c.PurchaseApproval.approval_received).handle({'id': 'purchase-001', 'decision': True}, approver, run_id='approve-001'))
        engine.handler(c.PurchaseApproval.dispatch, c.PurchaseApproval.scheduled).handle({'id': 'purchase-001'}, system, run_id='dispatch-001')
        engine.handler(c.PurchaseExecution.confirm, c.PurchaseExecution.confirmation_requested).handle({'id': 'purchase-001'}, system, run_id='confirm-001')
        print(services.application('purchase-001')['status'])


if __name__ == '__main__':
    main()
