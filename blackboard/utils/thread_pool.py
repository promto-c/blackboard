# Type Checking Imports
# ---------------------
from typing import Any, Optional, Generator, Callable

# Standard Library Imports
# ------------------------
from types import GeneratorType

# Third Party Imports
# -------------------
from qtpy import QtCore


# Class Definitions
# -----------------
class ThreadPoolManager:
    """A singleton manager for Qt QThreadPool.
    """

    _instance = None

    def __new__(cls, max_thread_count: Optional[int] = None):
        """Create or return the singleton instance of ThreadPoolManager.
        
        Args:
            max_thread_count (Optional[int]): The maximum number of threads in the pool.

        Returns:
            ThreadPoolManager: The singleton instance of the manager.
        """
        # Check if the singleton instance does not already exist
        if not cls._instance:
            # Create the singleton instance
            cls._instance = super().__new__(cls)
            cls._instance.pool = QtCore.QThreadPool()

            # Set the maximum number of threads if specified
            if max_thread_count:
                cls._instance.set_max_thread_count(max_thread_count)

        return cls._instance

    @classmethod
    def set_max_thread_count(cls, max_thread_count: int):
        """Set the maximum number of threads in the thread pool.
        
        Args:
            max_thread_count (int): The maximum number of threads.

        Raises:
            ValueError: If max_thread_count is less than or equal to 0.
        """
        if max_thread_count <= 0:
            raise ValueError("max_thread_count must be greater than 0")
        cls()._instance.pool.setMaxThreadCount(max_thread_count)

    @classmethod
    def thread_pool(cls) -> QtCore.QThreadPool:
        """Get the thread pool managed by the singleton instance.
        
        Returns:
            QtCore.QThreadPool: The thread pool instance.
        """
        return cls()._instance.pool

class RunnableTask(QtCore.QRunnable):
    """A Qt runnable task wrapper for executing a task with a 'run' method.
    """

    def __init__(self, task: QtCore.QObject):
        """Initialize the RunnableTask with a given task.
        
        Args:
            task (QtCore.QObject): The task to be executed, which should have a 'run' method.
        """
        super().__init__()
        self.task = task

    @QtCore.Slot()
    def run(self):
        """Execute the task's 'run' method if it exists and is callable.
        """
        if hasattr(self.task, 'run') and callable(getattr(self.task, 'run')):
            self.task.run()

class GeneratorWorker(QtCore.QObject):
    """A worker class that processes items from a generator and emits signals for various events.

    Signals:
        started (QtCore.Signal): Emitted to indicate fetching has started.
        error (QtCore.Signal): Emitted when an error occurs, passing the exception.
        result (QtCore.Signal): Emitted when a result item is fetched from the generator.
        finished (QtCore.Signal): Emitted when the fetching process has finished.
        loaded_all (QtCore.Signal): Emitted when no more data is available to fetch.
    """
    started = QtCore.Signal()
    error = QtCore.Signal(Exception)
    result = QtCore.Signal(object)
    finished = QtCore.Signal()
    loaded_all = QtCore.Signal()

    def __init__(self, generator: Optional[Generator[Any, None, None]] = None, is_pass_error: bool = False, desired_size: Optional[int] = None):
        """Initialize the GeneratorWorker with the given generator and desired size.

        Args:
            generator (Optional[Generator[Any, None, None]]): A generator object that yields items to be processed.
            is_pass_error (bool): If True, passes errors to the error signal; otherwise, raises them.
            desired_size (Optional[int]): The desired number of items to be processed from the generator.
        """
        super().__init__()
        self.generator = generator
        self.is_pass_error = is_pass_error
        self.desired_size = desired_size
        self._is_stopped = False
        self._is_paused = False
        self._mutex = QtCore.QMutex()

    def set_generator(self, generator: Generator[Any, None, None], desired_size: Optional[int] = None):
        """Set a new generator to be processed and optionally its desired size.

        Args:
            generator (Generator[Any, None, None]): A generator object that yields items to be processed.
            desired_size (Optional[int]): The desired number of items to be processed from the generator.
        """
        with QtCore.QMutexLocker(self._mutex):
            self.generator = generator
            self.desired_size = desired_size
            # Reset the stop flag when setting a new generator
            self._is_stopped = False
            self._is_paused = False

    @QtCore.Slot()
    def run(self):
        """Run the generator, emitting signals for each item, errors, and completion.
        """
        self.started.emit()
        count = 0

        # Iterate over the generator and emit each item
        try:
            for item in self.generator:
                # Lock the mutex to check the stop flag
                with QtCore.QMutexLocker(self._mutex):
                    if self._is_stopped:
                        break

                # Emit each generated item
                self.result.emit(item)
                count += 1

                # Lock the mutex to check the pause flag
                with QtCore.QMutexLocker(self._mutex):
                    if self._is_paused:
                        break

        except Exception as e:
            if self.is_pass_error:
                # Emit error if occurred
                self.error.emit(e)
            else:
                raise

        finally:
            # Emit finished signal
            self.finished.emit()

            # Check if no items are loaded
            if not count:
                self.loaded_all.emit()
            # Check if the desired size is set, not yet reached, and loading is not stopped
            elif self.desired_size is not None and count < self.desired_size and not self._is_paused:
                self.loaded_all.emit()
            # Check if the generator is a true generator (not a finite iterable) and the process was not manually stopped
            elif isinstance(self.generator, GeneratorType) and not self._is_paused:
                self.loaded_all.emit()

    def stop(self):
        """Stop the generator by setting the _is_stopped flag.
        """
        # Lock the mutex to set the stop flag safely
        with QtCore.QMutexLocker(self._mutex):
            self._is_stopped = True
            self._is_paused = True

    def pause(self):
        """Pause the generator by setting the _is_paused flag.
        """
        with QtCore.QMutexLocker(self._mutex):
            self._is_paused = True
