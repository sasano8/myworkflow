"""Public contract and execution failures."""
class ContractError(ValueError):
    pass


class RetryableError(Exception):
    pass


class ExecutionFailed(Exception):
    def __init__(self, step_id, cause, compensation_errors):
        self.step_id = step_id
        self.cause = cause
        self.compensation_errors = compensation_errors
        self.secondary_errors = ()
        super().__init__(f"{step_id}: {cause}; compensation failures: {compensation_errors}")
