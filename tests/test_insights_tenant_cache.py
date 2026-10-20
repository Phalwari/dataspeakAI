"""Offline tenant and cache isolation checks with mocked DB and Redis access."""

from types import SimpleNamespace

import pytest

import models
from services import db_pipeline_service as pipeline_module


class _UnexpectedDb:
    def query(self, _model):
        raise AssertionError("Database query must not run without a tenant ID")


class _TenantQuery:
    def __init__(self, connection):
        self.connection = connection
        self.filters = {}

    def filter(self, *conditions):
        for condition in conditions:
            self.filters[condition.left.key] = condition.right.value
        return self

    def first(self):
        if self.filters == {"id": 7, "tenant_id": 11}:
            return self.connection
        return None


class _TenantDb:
    def query(self, model):
        assert model is models.DatabaseConnection
        return _TenantQuery(SimpleNamespace())


@pytest.mark.parametrize("stream", [False, True])
def test_missing_tenant_rejected_before_db_or_cache(monkeypatch, stream):
    monkeypatch.setattr(
        pipeline_module, "cache_get",
        lambda _key: (_ for _ in ()).throw(AssertionError("Cache must not be read")),
    )
    service = pipeline_module.DatabasePipelineService()

    with pytest.raises(ValueError, match="Tenant ID is required"):
        if stream:
            next(service.run_db_pipeline_stream(db=_UnexpectedDb(), connection_id=7, user_id=3))
        else:
            service.run_db_pipeline(db=_UnexpectedDb(), connection_id=7, user_id=3)


@pytest.mark.parametrize("stream", [False, True])
def test_tenant_a_cached_result_is_not_read_by_tenant_b(monkeypatch, stream):
    tenant_a_key = pipeline_module._cache_key(11, 7, None, None, None)
    tenant_b_key = pipeline_module._cache_key(12, 7, None, None, None)
    assert tenant_a_key != tenant_b_key

    cached = {
        tenant_a_key: {
            "insights_version": pipeline_module.INSIGHTS_CACHE_VERSION,
            "connection_cache_version": 0,
            "marker": "tenant A result",
        }
    }
    lookups = []

    def fake_cache_get(key):
        lookups.append(key)
        return cached.get(key)

    monkeypatch.setattr(pipeline_module, "cache_get", fake_cache_get)
    service = pipeline_module.DatabasePipelineService()

    if stream:
        result = next(service.run_db_pipeline_stream(db=_TenantDb(), connection_id=7, tenant_id=11))
        assert result["data"]["marker"] == "tenant A result"
    else:
        result = service.run_db_pipeline(db=_TenantDb(), connection_id=7, tenant_id=11)
        assert result["marker"] == "tenant A result"
    assert lookups == [tenant_a_key]

    with pytest.raises(ValueError, match="not found or unauthorized"):
        if stream:
            next(service.run_db_pipeline_stream(db=_TenantDb(), connection_id=7, tenant_id=12))
        else:
            service.run_db_pipeline(db=_TenantDb(), connection_id=7, tenant_id=12)
    assert lookups == [tenant_a_key]
