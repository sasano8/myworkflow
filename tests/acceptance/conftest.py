import pytest

from examples.apps.purchase.acceptance.world import World


@pytest.fixture
def ctx(tmp_path, request):
    world = World(tmp_path)
    mutation = request.config.getoption('acceptance_fault')
    world.mutation = mutation
    if mutation == 'compensation':
        from myworkflow.executable import Context
        def omit_compensation(ctx: Context) -> None:
            pass
        world.registry.replace('c.delete-a', omit_compensation)
    if mutation == 'duplicate':
        # Deliberately faulty adapter: remove the storage guard as well as the event guard.
        with world.services.connect() as db:
            db.execute('DROP TABLE orders')
            db.execute('CREATE TABLE orders(id TEXT PRIMARY KEY, application_id TEXT)')
    try:
        yield world
    finally:
        try:
            request.node.acceptance_diagnostics = world.diagnose()
        finally:
            world.close()
