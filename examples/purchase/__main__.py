"""Run the documented purchase flow without external services."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from examples.purchase.contract import SPEC
from examples.purchase.handlers import registry
from examples.purchase import interfaces
from examples.purchase.services import Services
from myworkflow.executable import Engine, Principal, Program

program = Program(SPEC)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docs', action='store_true')
    args = parser.parse_args()
    if args.docs:
        print(program.documentation(registry), end='')
        return
    with TemporaryDirectory() as directory:
        services = Services(Path(directory) / 'purchase.db')
        engine = Engine(program, registry, services, interfaces)
        applicant = Principal('alice', frozenset({'role.requester'}))
        approver = Principal('bob', frozenset({'role.approver'}))
        system = Principal('scheduler', frozenset({'role.system'}))
        print(engine.invoke('b.submit', 't.submit', {'id': 'purchase-001', 'vendor': 'サンプル商事', 'amount': 10000}, applicant, run_id='submit-001'))
        print(engine.invoke('b.upload', 't.upload', {'id': 'purchase-001', 'file_a': '見積書A本文', 'file_b': '見積書B本文'}, applicant, run_id='upload-001'))
        print(engine.invoke('b.approve', 't.approve', {'id': 'purchase-001', 'decision': True}, approver, run_id='approve-001'))
        handoff = engine.invoke('b.dispatch', 't.timer', {'id': 'purchase-001'}, system, run_id='dispatch-001')
        engine.invoke('b.confirm', 't.confirm', {'id': handoff.application_id}, system, run_id='confirm-001')
        print(services.application('purchase-001')['status'])


if __name__ == '__main__':
    main()
