"""Tests for the API routes."""


class TestCreateRun:
    async def test_create_run_success(self, client):
        response = await client.post(
            "/api/v1/runs",
            json={
                "topic": "Test debate topic",
                "context": "Some background",
                "goal": "Decide something",
                "max_rounds": 3,
                "preset": "technical_decision",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == "Test debate topic"
        assert data["status"] == "pending"
        assert "id" in data

    async def test_create_run_minimal(self, client):
        response = await client.post(
            "/api/v1/runs",
            json={"topic": "Test", "goal": "Decide"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == "Test"
        assert data["max_rounds"] == 3  # default
        assert data["preset"] == "technical_decision"  # default

    async def test_create_run_validation_error(self, client):
        response = await client.post(
            "/api/v1/runs",
            json={"topic": ""},  # empty topic
        )
        assert response.status_code == 422


class TestGetRun:
    async def test_get_run_found(self, client):
        # Create first
        create_resp = await client.post(
            "/api/v1/runs",
            json={"topic": "Find me", "goal": "Test"},
        )
        run_id = create_resp.json()["id"]

        # Then get
        response = await client.get(f"/api/v1/runs/{run_id}")
        assert response.status_code == 200
        assert response.json()["topic"] == "Find me"

    async def test_get_run_not_found(self, client):
        response = await client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestListRuns:
    async def test_list_runs(self, client):
        # Create two runs
        resp_a = await client.post("/api/v1/runs", json={"topic": "Run A", "goal": "G"})
        resp_b = await client.post("/api/v1/runs", json={"topic": "Run B", "goal": "G"})
        id_a = resp_a.json()["id"]
        id_b = resp_b.json()["id"]

        response = await client.get("/api/v1/runs")
        assert response.status_code == 200
        data = response.json()
        # Runs should include our new ones
        returned_ids = {r["id"] for r in data}
        assert id_a in returned_ids
        assert id_b in returned_ids


class TestHealth:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
