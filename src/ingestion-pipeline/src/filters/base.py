from abc import ABC, abstractmethod
from typing import Any, List, Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")

class Filter(ABC, Generic[T, R]):
    @abstractmethod
    def process(self, data: T) -> R:
        """Process data and return result."""
        pass

class Pipeline:
    def __init__(self):
        self._filters: List[Filter] = []

    def add_filter(self, filter_instance: Filter) -> 'Pipeline':
        self._filters.append(filter_instance)
        return self

    def execute(self, initial_data: Any) -> Any:
        data = initial_data
        for filter_instance in self._filters:
            data = filter_instance.process(data)
        return data
