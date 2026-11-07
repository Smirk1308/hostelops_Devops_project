"""Tests for the /health endpoint."""


def test_health_success(client):
    """Test that /health returns status 200 and expected payload."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data.get('status') == 'ok'
    assert data.get('version') == '0.1.0'


def test_health_custom_version(app, client):
    """Test that /health reflects customized APP_VERSION in app config."""
    app.config['APP_VERSION'] = '1.2.0'
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data == {'status': 'ok', 'version': '1.2.0'}
