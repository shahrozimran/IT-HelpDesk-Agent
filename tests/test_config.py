from src.config import Settings


def test_settings_representation_does_not_disclose_credentials():
    settings = Settings(api_key="private-llm-test-value", pinecone_api_key="private-vector-test-value")
    description = repr(settings)
    assert "private-llm-test-value" not in description
    assert "private-vector-test-value" not in description
    assert settings.api_key == "private-llm-test-value"
    assert settings.pinecone_api_key == "private-vector-test-value"
