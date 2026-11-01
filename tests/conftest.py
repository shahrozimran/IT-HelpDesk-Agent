import pytest
from src.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", evidence_dir=tmp_path / "evidence",
                    model="controlled-test-model", api_key="test-only")
