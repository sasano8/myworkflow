import pytest

from examples.purchase.acceptance.world import World


@pytest.fixture
def ctx(tmp_path, request):
    world = World(tmp_path)
    mutation = request.config.getoption('--purchase-mutation')
    world.mutation = mutation
    if mutation == 'compensation':
        world.registry.handlers['c.delete-a'] = lambda ctx: None
    if mutation == 'duplicate':
        # Deliberately faulty adapter: remove the storage guard as well as the event guard.
        with world.services.connect() as db:
            db.execute('DROP TABLE orders')
            db.execute('CREATE TABLE orders(id TEXT PRIMARY KEY, application_id TEXT)')
    try:
        yield world
    finally:
        try:
            request.node.purchase_diagnostics = world.diagnose()
        finally:
            world.close()
