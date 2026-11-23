"""Mock API endpoints, called directly (no agent involved)."""


def test_list_vms_returns_all_10(api_client):
    r = api_client.get("/vms")
    assert r.status_code == 200
    assert len(r.json()) == 10


def test_list_vms_filters_by_status(api_client):
    vms = api_client.get("/vms", params={"status": "stopped"}).json()
    assert {v["vm_id"] for v in vms} == {"vm-002", "vm-003", "vm-005", "vm-006", "vm-009", "vm-010"}
    assert all(v["status"] == "stopped" for v in vms)


def test_list_vms_filters_by_project(api_client):
    vms = api_client.get("/vms", params={"project_id": "project-alpha"}).json()
    assert {v["vm_id"] for v in vms} == {"vm-001", "vm-002", "vm-003"}


def test_list_vms_has_no_activity_or_metrics(api_client):
    """Day 1 guarantee: inventory only, so the agent must call the per-VM endpoints."""
    vm = api_client.get("/vms").json()[0]
    for field in ("last_active", "days_inactive", "cpu_usage", "memory_gb"):
        assert field not in vm


def test_vm_activity_valid_id(api_client):
    r = api_client.get("/vms/vm-002/activity")
    assert r.status_code == 200
    body = r.json()
    assert body["vm_id"] == "vm-002"
    assert body["status"] == "stopped"
    assert body["days_inactive"] == 15
    assert "last_active" in body


def test_vm_activity_invalid_id_returns_404(api_client):
    r = api_client.get("/vms/vm-999/activity")
    assert r.status_code == 404
    assert "vm-999" in r.json()["detail"]


def test_vm_metrics_valid_id(api_client):
    r = api_client.get("/metrics/vm-004")
    assert r.status_code == 200
    body = r.json()
    assert body["cpu_usage_percent"] == 78.5
    assert body["memory_gb"] == 8


def test_list_projects_returns_all_3(api_client):
    projects = api_client.get("/projects").json()
    assert {p["project_id"] for p in projects} == {"project-alpha", "project-beta", "project-gamma"}
