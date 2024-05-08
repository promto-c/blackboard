# Type Checking Imports
# ---------------------
from typing import Any, Optional, Generator

# Standard Library Imports
# ------------------------
from types import GeneratorType

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
        super().__init__()
        self.task = task

    @QtCore.Slot()
    def run(self):
        # Check if the task object has a 'run' method and execute it
        if hasattr(self.task, 'run') and callable(getattr(self.task, 'run')):
            self.task.run()

class GeneratorWorker(QtCore.QObject):
    started = QtCore.Signal()           # Emit to indicate fetching has started
    error = QtCore.Signal(Exception)
    result = QtCore.Signal(object)
    finished = QtCore.Signal()
    loaded_all = QtCore.Signal()        # Emit when no more data is available to fetch

    def __init__(self, generator: Optional[Generator[Any, None, None]] = None, is_pass_error: bool = False, desired_size: Optional[int] = None):
        """Initializes the GeneratorWorker with the given generator and desired size.

        Args:
            generator: A generator object that yields items to be processed.
            is_pass_error (bool): If True, passes errors to the error signal; otherwise, raises them.
            desired_size (Optional[int]): The desired number of items to be processed from the generator.
        """
        super().__init__()
        self.generator = generator
        self.is_pass_error = is_pass_error
        self.desired_size = desired_size
        self.is_stopped = False
        self._mutex = QtCore.QMutex()

    def set_generator(self, generator: Generator[Any, None, None], desired_size: Optional[int] = None):
        """Sets a new generator to be processed and optionally its desired size.

        Args:
            generator: A generator object that yields items to be processed.
            desired_size (Optional[int]): The desired number of items to be processed from the generator.
        """
        with QtCore.QMutexLocker(self._mutex):
            self.generator = generator
            self.desired_size = desired_size
            # Reset the stop flag when setting a new generator
            self.is_stopped = False

    @QtCore.Slot()
    def run(self):
        """Runs the generator, emitting signals for each item, errors, and completion.
        """
        self.started.emit()
        count = 0
        try:
            for item in self.generator:
                # Emit each generated item
                self.result.emit(item)
                count += 1

                # Lock the mutex to check the stop flag
                with QtCore.QMutexLocker(self._mutex):
                    if self.is_stopped:
                        break

        except Exception as e:
            if self.is_pass_error:
                # Emit error if occurred
                self.error.emit(e)
            else:
                raise

        finally:
            # Signal completion
            self.finished.emit()

            # Check if no items are loaded
            if not count:
                self.loaded_all.emit()
            # Check if the desired size is set, not yet reached, and loading is not stopped
            elif self.desired_size is not None and count < self.desired_size and not self.is_stopped:
                self.loaded_all.emit()
            # Check if the generator is still running and loading is not stopped
            elif isinstance(self.generator, GeneratorType) and not self.is_stopped:
                self.loaded_all.emit()

    def stop(self):
        """Stops the generator by setting the is_stopped flag.
        """
        # Lock the mutex to set the stop flag safely
        with QtCore.QMutexLocker(self._mutex):
            self.is_stopped = True
