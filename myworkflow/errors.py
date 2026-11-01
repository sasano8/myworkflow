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


class PipelineError(Exception):
    """An explicitly coded failure. Codes are application codes, not HTTP statuses."""
    def __init__(self, code: int, message: str, *, level='error'):
        from myworkflow.results import Message
        if type(code) is not int or code <= 0:
            raise ValueError('Failure code must be a positive integer')
        Message(level, message)
        self.code, self.level = code, level
        super().__init__(message)


class BusinessError(PipelineError, ValueError):
    """Expected rejection: return a result to Temporal rather than retrying the activity."""
