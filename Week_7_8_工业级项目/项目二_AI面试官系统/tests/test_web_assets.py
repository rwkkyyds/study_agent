import re


def test_web_index_is_served(client):
    response = client.get("/web/")

    assert response.status_code == 200
    assert "AI 面试官系统" in response.text
    assert 'id="app"' in response.text


def test_web_console_entry_is_served(client):
    response = client.get("/web/console")

    assert response.status_code == 200
    assert 'id="app"' in response.text


def test_web_candidate_entry_is_served(client):
    response = client.get("/web/candidate")

    assert response.status_code == 200
    assert 'id="app"' in response.text


def test_web_vite_assets_are_served(client):
    index_response = client.get("/web/")
    asset_paths = re.findall(r'/(web/assets/[^"\']+\.(?:js|css))', index_response.text)

    assert asset_paths

    responses = [client.get(f"/{path}") for path in asset_paths]

    assert all(response.status_code == 200 for response in responses)
    assert any("EventSource" in response.text for response in responses)
    assert any("AI 面试官" in response.text for response in responses)
    assert any(".candidate-room" in response.text for response in responses)
    assert any("Interview invitation" in response.text for response in responses)
    assert any(".candidate-invite" in response.text for response in responses)
    assert any("草稿自动保存" in response.text for response in responses)
    assert any("继续上次面试" in response.text for response in responses)
    assert any("/hiring/interview-sessions/" in response.text for response in responses)
    assert any("/interviews/questions/async" in response.text for response in responses)
    assert any("/interviews/follow-up/async" in response.text for response in responses)
    assert any("/interviews/evaluate/async" in response.text for response in responses)
    assert any("/interviews/tasks/" in response.text for response in responses)
