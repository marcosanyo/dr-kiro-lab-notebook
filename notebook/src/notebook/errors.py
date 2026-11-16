"""The one error type of the notebook build (design "Error Handling")."""


class NotebookError(Exception):
    """A check failed. `where` is a file (with line or entry), an option or a choice key; `problem` says what
    is wrong. The command line prints it as `notebook-build: <where>: <problem>`."""

    def __init__(self, where: str, problem: str) -> None:
        if not where:
            raise ValueError("NotebookError needs a non-empty where")
        if not problem:
            raise ValueError("NotebookError needs a non-empty problem")
        super().__init__(f"{where}: {problem}")
        self.where = where
        self.problem = problem
