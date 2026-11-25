"""Mock API endpoints, called directly (no agent involved)."""


def test_list_vms_returns_inventory_only(api_client):
    """/vms must not include activity or metrics, so the agent has to call the per-VM endpoints."""
    vms = api_client.get("/vms").json()
    assert len(vms) == 10
    for field in ("last_active", "days_inactive", "cpu_usage", "memory_gb"):
        assert field not in vms[0]


def test_list_vms_filters_by_status(api_client):
    vms = api_client.get("/vms", params={"status": "stopped"}).json()
    assert {v["vm_id"] for v in vms} == {"vm-002", "vm-003", "vm-005", "vm-006", "vm-009", "vm-010"}


def test_list_vms_rejects_unknown_status(api_client):
    r = api_client.get("/vms", params={"status": "paused"})
    assert r.status_code == 422


def test_vm_activity_returns_days_inactive(api_client):
    body = api_client.get("/vms/vm-002/activity").json()
    assert body["vm_id"] == "vm-002"
    assert body["days_inactive"] == 15
