"""Optional bounded-lifetime Temporal test resources."""

from contextlib import AsyncExitStack


class TemporalHarness:
    def __init__(self, executable, task_queue, *, workflows, activities):
        self.executable, self.task_queue = executable, task_queue
        self.workflows, self.activities = workflows, activities
        self._stack = AsyncExitStack()

    async def __aenter__(self):
        from temporalio.testing import WorkflowEnvironment
        from temporalio.worker import Worker

        try:
            self.environment = await WorkflowEnvironment.start_local(
                dev_server_existing_path=self.executable
            )
            self._stack.push_async_callback(self.environment.shutdown)
            self.worker = Worker(
                self.environment.client,
                task_queue=self.task_queue,
                workflows=self.workflows,
                activities=self.activities,
            )
            await self._stack.enter_async_context(self.worker)
            self.client = self.environment.client
            return self
        except BaseException:
            await self._stack.aclose()
            raise

    async def __aexit__(self, *args):
        await self._stack.aclose()
