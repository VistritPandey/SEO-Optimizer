from pathlib import Path

import pytest

from seo_optimizer.contracts import BenchmarkCase, ResponseRecord
from seo_optimizer.evaluation import load_cases, load_responses
from seo_optimizer.knowledge import KnowledgePackage, load_knowledge

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def knowledge() -> KnowledgePackage:
    return load_knowledge()


@pytest.fixture
def cases(knowledge: KnowledgePackage) -> dict[str, BenchmarkCase]:
    return {case.id: case for case in load_cases(FIXTURES / "cases.json", knowledge)}


@pytest.fixture
def records() -> dict[str, ResponseRecord]:
    return {
        record.case_id: record for record in load_responses(FIXTURES / "reference-responses.json")
    }
