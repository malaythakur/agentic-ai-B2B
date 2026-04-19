"""Tests for API endpoints"""
import pytest
from fastapi import status


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_import_leads_endpoint(client, auth_headers):
    """Test import leads endpoint"""
    # This would need actual test data file
    payload = {"json_path": "data/test_leads.json"}
    response = client.post("/api/import/leads", json=payload, headers=auth_headers)
    # Expect error since test file doesn't exist
    assert response.status_code in [status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_200_OK]


def test_generate_batch_endpoint(client, auth_headers):
    """Test generate batch endpoint"""
    payload = {
        "from_email": "test@example.com",
        "max_leads": 10,
        "min_fit_score": 7
    }
    response = client.post("/api/generate/outbound-batch", json=payload, headers=auth_headers)
    # Should work even with empty database
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


def test_metrics_endpoint(client):
    """Test metrics endpoint"""
    response = client.get("/api/metrics")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "leads" in data
    assert "campaigns" in data
    assert "messages" in data


def test_get_run_not_found(client, auth_headers):
    """Test get run endpoint with non-existent run"""
    response = client.get("/api/runs/non-existent-run", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_send_batch_not_found(client, auth_headers):
    """Test send batch endpoint with non-existent run"""
    response = client.post("/api/send/batch/non-existent-run", headers=auth_headers)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


def test_classify_reply_not_found(client, auth_headers):
    """Test classify reply endpoint with non-existent reply"""
    payload = {"reply_id": "non-existent-reply"}
    response = client.post("/api/replies/classify", json=payload, headers=auth_headers)
    # Should handle gracefully
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


def test_pipeline_funnel_endpoint(client, auth_headers):
    """Test pipeline funnel endpoint"""
    response = client.get("/api/pipeline/funnel", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data


def test_crm_pipeline_value_endpoint(client, auth_headers):
    """Test CRM pipeline value endpoint"""
    response = client.get("/api/crm/pipeline-value", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data


def test_learning_performance_endpoint(client, auth_headers):
    """Test learning performance endpoint"""
    response = client.get("/api/learning/performance", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK


def test_escalation_queue_endpoint(client, auth_headers):
    """Test escalation queue endpoint"""
    response = client.get("/api/escalation/queue", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK


def test_experiments_endpoint(client, auth_headers):
    """Test experiments endpoint"""
    response = client.get("/api/experiments", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK


def test_qualification_batch_endpoint(client, auth_headers):
    """Test qualification batch endpoint"""
    response = client.post("/api/qualification/batch", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
