# Type Checking Imports
# ---------------------
from typing import Optional

# Third Party Imports
# -------------------
from qtpy import QtCore


# Class Definitions
# -----------------
class ThreadPoolManager:
    _instance = None

    def __new__(cls, max_thread_count: Optional[int] = None):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.pool = QtCore.QThreadPool()

            if max_thread_count:
                cls._instance.pool.setMaxThreadCount(max_thread_count)

        return cls._instance

    @classmethod
    def thread_pool(cls) -> QtCore.QThreadPool:
        return cls()._instance.pool

class RunnableTask(QtCore.QRunnable):
    def __init__(self, task):
        super(RunnableTask, self).__init__()
        self.task = task

    @QtCore.Slot()
    def run(self):
        # Check if the task object has a 'run' method
        if hasattr(self.task, 'run') and callable(getattr(self.task, 'run')):
            self.task.run()  # Execute the 'run' method of the task
