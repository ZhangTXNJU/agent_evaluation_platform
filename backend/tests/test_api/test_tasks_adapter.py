"""
任务 API 集成测试 — 重点覆盖 adapter 改造相关行为

注:这些测试不会触发后台 executor(因为 lifespan 没启动),所以任务会停留在 pending,
正好用来验证创建/读取流程中 adapter_type / adapter_config 字段的端到端流转。
"""

import pytest


# ── 准备 fixture: 在测试 DB 中插入一个数据集 ────────────────────
@pytest.fixture
def seeded_dataset(client, test_db):
    _, SessionLocal = test_db
    from models.dataset import Dataset

    db = SessionLocal()
    try:
        ds = Dataset(
            name="test_ds_for_adapter",
            description="for tests",
            cases=[
                {"id": "c1", "input": "去北京3天", "difficulty": "easy"},
                {"id": "c2", "input": "去上海5天", "difficulty": "easy"},
            ],
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)
        return ds.id
    finally:
        db.close()


# ── /api/v1/adapters & /endpoint-presets ───────────────────────
class TestAdapterMetaEndpoints:
    def test_list_adapters(self, client):
        r = client.get("/api/v1/adapters")
        assert r.status_code == 200
        body = r.json()
        assert "native" in body
        assert "openai_chat" in body

    def test_list_endpoint_presets(self, client):
        r = client.get("/api/v1/endpoint-presets")
        assert r.status_code == 200
        presets = r.json()
        assert isinstance(presets, list)
        assert len(presets) > 0
        # 必须有 native_local 默认项
        keys = [p["key"] for p in presets]
        assert "native_local" in keys
        # 每项结构完整
        for p in presets:
            assert {
                "key",
                "label",
                "description",
                "adapter_type",
                "agent_endpoint",
                "adapter_config",
            } <= set(p.keys())


# ── 任务创建: 默认 adapter_type 向后兼容 ────────────────────────
class TestTaskCreateBackwardCompat:
    def test_create_task_without_adapter_field_defaults_to_native(
        self, client, seeded_dataset
    ):
        """旧前端不传 adapter_type 字段也能创建任务,默认 native"""
        r = client.post(
            "/api/v1/tasks",
            json={
                "name": "old_style_task",
                "agent_version": "v1",
                "dataset_id": seeded_dataset,
                "metrics": ["success_rate"],
                "agent_endpoint": "http://localhost:8000/api/eval/run",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["adapter_type"] == "native"

    def test_create_task_with_explicit_native(self, client, seeded_dataset):
        r = client.post(
            "/api/v1/tasks",
            json={
                "name": "explicit_native",
                "agent_version": "v1",
                "dataset_id": seeded_dataset,
                "metrics": ["success_rate"],
                "agent_endpoint": "http://localhost:8000/api/eval/run",
                "adapter_type": "native",
                "adapter_config": {},
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["adapter_type"] == "native"


# ── 任务创建: openai_chat ──────────────────────────────────────
class TestTaskCreateOpenAIChat:
    def test_create_with_openai_chat(self, client, seeded_dataset):
        r = client.post(
            "/api/v1/tasks",
            json={
                "name": "openai_task",
                "agent_version": "deepseek-v1",
                "dataset_id": seeded_dataset,
                "metrics": ["success_rate", "tool_accuracy"],
                "agent_endpoint": "https://api.deepseek.com/v1/chat/completions",
                "adapter_type": "openai_chat",
                "adapter_config": {"model": "deepseek-chat", "api_key": "sk-test"},
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["adapter_type"] == "openai_chat"

        # 拉取详情,确认 adapter_config 也持久化了
        task_id = body["id"]
        detail = client.get(f"/api/v1/tasks/{task_id}").json()
        assert detail["adapter_type"] == "openai_chat"
        assert detail["adapter_config"]["model"] == "deepseek-chat"
        assert detail["adapter_config"]["api_key"] == "sk-test"


# ── 任务创建: 错误处理 ─────────────────────────────────────────
class TestTaskCreateValidation:
    def test_unknown_adapter_type_rejected(self, client, seeded_dataset):
        r = client.post(
            "/api/v1/tasks",
            json={
                "name": "bad_adapter",
                "agent_version": "v1",
                "dataset_id": seeded_dataset,
                "metrics": ["success_rate"],
                "agent_endpoint": "http://x",
                "adapter_type": "nonexistent_xyz",
            },
        )
        assert r.status_code == 400
        assert "未知" in r.json()["detail"] or "nonexistent_xyz" in r.json()["detail"]

    def test_unknown_metric_rejected(self, client, seeded_dataset):
        """已存在的校验,确保改造没破坏指标校验"""
        r = client.post(
            "/api/v1/tasks",
            json={
                "name": "bad_metric",
                "agent_version": "v1",
                "dataset_id": seeded_dataset,
                "metrics": ["unknown_metric"],
                "agent_endpoint": "http://x",
            },
        )
        assert r.status_code == 422  # pydantic validator 抛 ValidationError → 422


# ── 任务列表 / 详情中带出 adapter_type ──────────────────────────
class TestTaskListContainsAdapterType:
    def test_list_includes_adapter_type(self, client, seeded_dataset):
        # 先创建
        client.post(
            "/api/v1/tasks",
            json={
                "name": "for_list",
                "agent_version": "v1",
                "dataset_id": seeded_dataset,
                "metrics": ["success_rate"],
                "adapter_type": "openai_chat",
                "adapter_config": {"model": "x"},
            },
        )
        # 列表
        r = client.get("/api/v1/tasks")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        target = [t for t in items if t["name"] == "for_list"][0]
        assert target["adapter_type"] == "openai_chat"


# ── 状态机: draft → pending → ... ─────────────────────────────
class TestTaskStatusMachine:
    def test_create_task_starts_in_draft_state(self, client, seeded_dataset):
        """创建后应当为 'draft' 状态,executor 不会自动跑"""
        r = client.post(
            "/api/v1/tasks",
            json={
                "name": "draft_state_test",
                "agent_version": "v1",
                "dataset_id": seeded_dataset,
                "metrics": ["success_rate"],
            },
        )
        assert r.status_code == 201
        assert r.json()["status"] == "draft"

    def test_execute_transitions_draft_to_pending(self, client, seeded_dataset):
        """点击执行后应当从 draft 转到 pending"""
        r = client.post(
            "/api/v1/tasks",
            json={
                "name": "execute_draft",
                "agent_version": "v1",
                "dataset_id": seeded_dataset,
                "metrics": ["success_rate"],
            },
        )
        task_id = r.json()["id"]
        assert r.json()["status"] == "draft"

        r2 = client.post(f"/api/v1/tasks/{task_id}/execute")
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "pending"

    def test_done_task_cannot_be_re_executed(self, client, seeded_dataset, test_db):
        """done 状态的任务不允许通过 execute 接口覆盖,应返回 409"""
        # 直接造一个 done 状态的任务到 DB
        _, SessionLocal = test_db
        from models.task import Task

        db = SessionLocal()
        try:
            t = Task(
                name="already_done",
                agent_version="v1",
                dataset_id=seeded_dataset,
                metrics=["success_rate"],
                agent_endpoint="http://x",
                status="done",
                progress_total=1,
                progress_current=1,
            )
            db.add(t)
            db.commit()
            db.refresh(t)
            tid = t.id
        finally:
            db.close()

        r = client.post(f"/api/v1/tasks/{tid}/execute")
        assert r.status_code == 409
        assert "重跑" in r.json()["detail"]
