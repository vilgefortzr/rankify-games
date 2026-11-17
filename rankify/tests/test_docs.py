import pytest
import yaml

pytestmark = pytest.mark.django_db


def test_openapi_schema_describes_collections(api_client):
    response = api_client.get("/api/schema/")

    assert response.status_code == 200
    schema = yaml.safe_load(response.content)
    collections = schema["paths"]["/api/v1/collections/{collection_id}/"]
    assert set(collections) >= {"get", "patch", "delete"}
    assert set(collections["patch"]["responses"]) == {"200", "400", "401", "403", "404"}


def test_swagger_ui_opens(api_client):
    response = api_client.get("/api/docs/")

    assert response.status_code == 200
    assert b"/api/schema/" in response.content
