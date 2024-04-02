# Type Checking Imports
# ---------------------
from typing import Optional, Generator

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

class GeneratorWorker(QtCore.QObject):
    started = QtCore.Signal()           # Emit to indicate fetching has started
    error = QtCore.Signal(Exception)
    result = QtCore.Signal(object)
    finished = QtCore.Signal()
    loaded_all = QtCore.Signal()        # Emit when no more data is available to fetch

    def __init__(self, generator, is_pass_error: bool = False):
        super().__init__()
        self.generator = generator
        self.is_pass_error = is_pass_error
        self.is_stopped = False

    def run(self):
        self.started.emit()
        is_loaded_any = False
        try:
            for item in self.generator:
                # Emit each generated item
                self.result.emit(item)
                is_loaded_any = True

                # Exit the loop if is_stopped
                if self.is_stopped:
                    break

            if not is_loaded_any:
                self.loaded_all.emit()

        except Exception as e:
            if self.is_pass_error:
                # Emit error if occurred
                self.error.emit(e)
            else:
                raise(e)

        finally:
            # Signal completion
            self.finished.emit()
            if isinstance(self.generator, Generator) and not self.is_stopped:
                self.loaded_all.emit()

    def stop(self):
        self.is_stopped = True
