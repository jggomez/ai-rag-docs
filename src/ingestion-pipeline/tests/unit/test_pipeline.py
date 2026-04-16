import pytest
from src.filters.base import Filter, Pipeline

class AddOneFilter(Filter[int, int]):
    def process(self, data: int) -> int:
        return data + 1

class MultiplyByTwoFilter(Filter[int, int]):
    def process(self, data: int) -> int:
        return data * 2

def test_pipeline_execution():
    pipeline = Pipeline()
    pipeline.add_filter(AddOneFilter())
    pipeline.add_filter(MultiplyByTwoFilter())
    
    result = pipeline.execute(5)
    
    # (5 + 1) * 2 = 12
    assert result == 12

def test_pipeline_empty():
    pipeline = Pipeline()
    assert pipeline.execute(10) == 10
