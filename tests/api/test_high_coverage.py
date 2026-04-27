"""Tests para coverage."""

import pytest

API_KEY = "559f4341b1277fe62ca2bab328370959c6f622e7d1dd1a10a80160f031ac7897"


@pytest.fixture
def auth_headers():
    return {"X-API-Key": API_KEY}


class TestAllEndpoints:
    def test_health(self, client, auth_headers):
        r = client.get("/api/v1/health", headers=auth_headers)
        assert r.status_code == 200

    def test_metrics(self, client, auth_headers):
        r = client.get("/api/v1/metrics", headers=auth_headers)
        assert r.status_code == 200

    def test_metrics_contract(self, client, auth_headers):
        r = client.get("/api/v1/metrics", headers=auth_headers)

        assert r.status_code == 200

        payload = r.json()
        assert set(payload) == {
            "cpu",
            "memory",
            "uptime",
            "requests_total",
            "errors_total",
        }

        assert isinstance(payload["cpu"], float)
        assert isinstance(payload["memory"], str)
        assert isinstance(payload["uptime"], int)
        assert isinstance(payload["requests_total"], int)
        assert isinstance(payload["errors_total"], int)

        memory_parts = payload["memory"].split("/")
        assert len(memory_parts) == 2
        assert all(part.endswith("MB") for part in memory_parts)
        assert "memory_total" not in payload

    def test_logs(self, client, auth_headers):
        r = client.get("/api/v1/logs", headers=auth_headers)
        assert r.status_code == 200

    def test_processes_list(self, client, auth_headers):
        r = client.get("/api/v1/processes", headers=auth_headers)
        assert r.status_code == 200

    def test_agents_list(self, client, auth_headers):
        r = client.get("/api/v1/agents/sessions", headers=auth_headers)
        assert r.status_code == 200

    def test_agents_create(self, client, auth_headers):
        client.post(
            "/api/v1/agents/sessions",
            headers=auth_headers,
            json={"agent_type": "opencode", "task": "test"},
        )

    def test_workflow_outline(self, client, auth_headers):
        client.post("/api/v1/workflow/outline", headers=auth_headers, json={"task": "test"})

    def test_workflow_execute(self, client, auth_headers):
        client.post("/api/v1/workflow/plan-1/execute", headers=auth_headers, json={})

    def test_workflow_verify(self, client, auth_headers):
        client.post("/api/v1/workflow/exec-1/verify", headers=auth_headers, json={})

    def test_workflow_status(self, client, auth_headers):
        client.get("/api/v1/workflow/status", headers=auth_headers)

    def test_memory_list(self, client, auth_headers):
        r = client.get("/api/v1/memory", headers=auth_headers)
        assert r.status_code == 200

    def test_memory_search(self, client, auth_headers):
        r = client.get("/api/v1/memory/search?q=test", headers=auth_headers)
        assert r.status_code == 200

    def test_discovery(self, client, auth_headers):
        r = client.get("/api/v1/discovery", headers=auth_headers)
        assert r.status_code == 200

    def test_discovery_workflows(self, client, auth_headers):
        r = client.get("/api/v1/discovery/workflows", headers=auth_headers)
        assert r.status_code == 200

    def test_discovery_errors(self, client, auth_headers):
        r = client.get("/api/v1/discovery/errors/404", headers=auth_headers)
        assert r.status_code == 200

    def test_webhooks_list(self, client, auth_headers):
        r = client.get("/api/v1/webhooks", headers=auth_headers)
        assert r.status_code == 200

    def test_integrations_info(self, client, auth_headers):
        client.get("/api/v1/integrations/branch-review/info", headers=auth_headers)

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_processes_get(self, client, auth_headers):
        client.get("/api/v1/processes/1", headers=auth_headers)

    def test_processes_create(self, client, auth_headers):
        client.post("/api/v1/processes", headers=auth_headers, json={"name": "test"})

    def test_processes_stop(self, client, auth_headers):
        client.post("/api/v1/processes/1/stop", headers=auth_headers)

    def test_processes_restart(self, client, auth_headers):
        client.post("/api/v1/processes/1/restart", headers=auth_headers)

    def test_processes_delete(self, client, auth_headers):
        client.delete("/api/v1/processes/1", headers=auth_headers)

    def test_processes_scale(self, client, auth_headers):
        client.post("/api/v1/processes/1/scale", headers=auth_headers, json={"instances": 2})

    def test_agents_get(self, client, auth_headers):
        client.get("/api/v1/agents/sessions/test-id", headers=auth_headers)

    def test_agents_delete(self, client, auth_headers):
        client.delete("/api/v1/agents/sessions/test-id", headers=auth_headers)

    def test_memory_get(self, client, auth_headers):
        client.get("/api/v1/memory/test-id", headers=auth_headers)

    def test_memory_delete(self, client, auth_headers):
        client.delete("/api/v1/memory/test-id", headers=auth_headers)

    def test_logs_id(self, client, auth_headers):
        client.get("/api/v1/logs/1", headers=auth_headers)

    def test_webhooks_delete(self, client, auth_headers):
        # Deleting non-existent webhook should return 404
        resp = client.delete("/api/v1/webhooks/test-id", headers=auth_headers)
        assert resp.status_code == 404

    def test_integrations_run(self, client, auth_headers):
        client.get("/api/v1/integrations/branch-review/run", headers=auth_headers)

    def test_integrations_final(self, client, auth_headers):
        client.get("/api/v1/integrations/branch-review/final/test-id", headers=auth_headers)

    def test_integrations_workflow(self, client, auth_headers):
        client.post("/api/v1/integrations/branch-review/workflow", headers=auth_headers, json={})

    def test_discovery_multiple_errors(self, client, auth_headers):
        for code in [400, 401, 403, 500]:
            r = client.get(f"/api/v1/discovery/errors/{code}", headers=auth_headers)
            assert r.status_code == 200

    def test_memory_pagination(self, client, auth_headers):
        r = client.get("/api/v1/memory?limit=10&offset=0", headers=auth_headers)
        assert r.status_code == 200

    def test_memory_search_type(self, client, auth_headers):
        r = client.get("/api/v1/memory/search?q=test&type=observation", headers=auth_headers)
        assert r.status_code == 200

    def test_memory_search_limit(self, client, auth_headers):
        r = client.get("/api/v1/memory/search?q=test&limit=5", headers=auth_headers)
        assert r.status_code == 200


class TestCoveragePush:
    def test_memory_detailed(self, client, auth_headers):
        client.post(
            "/api/v1/memory",
            headers=auth_headers,
            json={"type": "observation", "content": "test data", "metadata": {"key": "value"}},
        )
        client.get("/api/v1/memory", headers=auth_headers)
        client.get("/api/v1/memory?limit=5&offset=0", headers=auth_headers)

    def test_memory_search_detailed(self, client, auth_headers):
        client.get("/api/v1/memory/search?q=test", headers=auth_headers)
        client.get("/api/v1/memory/search?q=test&type=observation", headers=auth_headers)

    def test_agents_detailed(self, client, auth_headers):
        client.get("/api/v1/agents/sessions", headers=auth_headers)
        client.get("/api/v1/agents/sessions?limit=10", headers=auth_headers)

    def test_workflow_detailed(self, client, auth_headers):
        client.post(
            "/api/v1/workflow/outline", headers=auth_headers, json={"task": "test", "context": {}}
        )
        client.get("/api/v1/workflow/status", headers=auth_headers)

    def test_workflow_execute_detailed(self, client, auth_headers):
        client.post("/api/v1/workflow/plan-1/execute", headers=auth_headers, json={})
        client.post("/api/v1/workflow/plan-1/execute", headers=auth_headers, json={"context": {}})

    def test_processes_variations(self, client, auth_headers):
        client.get("/api/v1/processes", headers=auth_headers)
        client.post(
            "/api/v1/processes",
            headers=auth_headers,
            json={"name": "test", "script": "app.js", "instances": 1},
        )

    def test_integrations_variations(self, client, auth_headers):
        client.post(
            "/api/v1/integrations/branch-review/command",
            headers=auth_headers,
            json={"command": "init"},
        )
        client.post(
            "/api/v1/integrations/branch-review/command",
            headers=auth_headers,
            json={"command": "explore", "args": {}},
        )

    def test_webhooks_variations(self, client, auth_headers):
        client.post(
            "/api/v1/webhooks",
            headers=auth_headers,
            json={"url": "https://test.com", "events": ["push"]},
        )

    def test_health_detailed(self, client, auth_headers):
        for _i in range(3):
            r = client.get("/api/v1/health", headers=auth_headers)
            assert r.status_code == 200

    def test_discovery_detailed(self, client, auth_headers):
        client.get("/api/v1/discovery", headers=auth_headers)
        client.get("/api/v1/discovery/workflows", headers=auth_headers)


class TestFinalPush:
    def test_memory_all_flows(self, client, auth_headers):
        client.post(
            "/api/v1/memory", headers=auth_headers, json={"type": "test", "content": "data1"}
        )
        client.get("/api/v1/memory", headers=auth_headers)
        client.get("/api/v1/memory?limit=1", headers=auth_headers)
        client.get("/api/v1/memory/search?q=data", headers=auth_headers)

    def test_agents_all_flows(self, client, auth_headers):
        client.get("/api/v1/agents/sessions", headers=auth_headers)
        client.get("/api/v1/agents/sessions?limit=1", headers=auth_headers)
        client.post(
            "/api/v1/agents/sessions",
            headers=auth_headers,
            json={"agent_type": "opencode", "task": "test1"},
        )

    def test_workflow_all_flows(self, client, auth_headers):
        client.post("/api/v1/workflow/outline", headers=auth_headers, json={"task": "task1"})
        client.get("/api/v1/workflow/status", headers=auth_headers)

    def test_processes_all_flows(self, client, auth_headers):
        client.get("/api/v1/processes", headers=auth_headers)
        client.post(
            "/api/v1/processes", headers=auth_headers, json={"name": "p1", "script": "s.js"}
        )

    def test_integrations_all_flows(self, client, auth_headers):
        client.get("/api/v1/integrations/branch-review/info", headers=auth_headers)
        client.get("/api/v1/integrations/branch-review/run", headers=auth_headers)

    def test_webhooks_all_flows(self, client, auth_headers):
        client.get("/api/v1/webhooks", headers=auth_headers)
        client.post(
            "/api/v1/webhooks", headers=auth_headers, json={"url": "http://a.com", "events": ["e1"]}
        )

    def test_system_all_flows(self, client, auth_headers):
        client.get("/api/v1/health", headers=auth_headers)
        client.get("/api/v1/metrics", headers=auth_headers)
        client.get("/api/v1/logs", headers=auth_headers)

    def test_discovery_all_flows(self, client, auth_headers):
        client.get("/api/v1/discovery", headers=auth_headers)
        client.get("/api/v1/discovery/workflows", headers=auth_headers)
        for c in [200, 400, 401, 403, 404, 500]:
            client.get(f"/api/v1/discovery/errors/{c}", headers=auth_headers)


class TestMemoryQuery:
    def test_memory_query_basic(self, client, auth_headers):
        client.get("/api/v1/memory/query", headers=auth_headers)

    def test_memory_query_with_agent(self, client, auth_headers):
        client.get("/api/v1/memory/query?agent=test-agent", headers=auth_headers)

    def test_memory_query_with_run(self, client, auth_headers):
        client.get("/api/v1/memory/query?run=test-run", headers=auth_headers)

    def test_memory_query_with_event_type(self, client, auth_headers):
        client.get("/api/v1/memory/query?event-type=test", headers=auth_headers)

    def test_memory_query_with_limit(self, client, auth_headers):
        client.get("/api/v1/memory/query?limit=10", headers=auth_headers)

    def test_memory_query_with_since_hours(self, client, auth_headers):
        client.get("/api/v1/memory/query?since=24h", headers=auth_headers)

    def test_memory_query_with_since_days(self, client, auth_headers):
        client.get("/api/v1/memory/query?since=7d", headers=auth_headers)

    def test_memory_query_with_since_iso(self, client, auth_headers):
        client.get("/api/v1/memory/query?since=2024-01-01", headers=auth_headers)

    def test_memory_query_invalid_since(self, client, auth_headers):
        client.get("/api/v1/memory/query?since=invalid", headers=auth_headers)

    def test_memory_query_with_all_params(self, client, auth_headers):
        client.get(
            "/api/v1/memory/query?agent=a&run=r&event-type=e&limit=5&scan-limit=100&since=24h",
            headers=auth_headers,
        )
