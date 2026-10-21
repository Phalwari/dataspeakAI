"""Synthetic regressions for the defects reproduced by live demo acceptance QA."""
import json
import sqlite3
from decimal import Decimal
import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

import models
from search.hybrid import reciprocal_rank_fusion
from services.citation_service import CitationService
from services.mongo_query import validate_plan
from services.mongo_query import bind_date_filters
from services import db_pipeline_service as pipeline, db_pool, db_utils


def test_rrf_keeps_distinct_passages_without_chunk_index():
    passages = [{"content":text,"metadata":{"document_id":5,"chunk_id":idx}}
                for idx,text in [(100,"Return policy: 30 days"),(101,"Revenue definitions")]]
    fused = reciprocal_rank_fusion(passages, passages[:1], top_k=5)
    assert len(fused) == 2
    assert fused[0]["metadata"]["chunk_id"] == 100
    # Legacy indexes without chunk IDs must also preserve distinct text.
    for passage in passages:
        passage["metadata"].pop("chunk_id")
    assert len(reciprocal_rank_fusion(passages, [], top_k=5)) == 2


def test_claims_exclude_source_page_markers_and_followup_questions():
    claims, _ = CitationService().extract_claims_with_stats(
        "## Return policy\nUnopened equipment may be returned within 30 days. [Source: policy.txt, p. 1]\n"
        "**Suggested Follow-ups:**\n1. How do I return equipment?\n2. Can I exchange it?", parse_tables=True)
    assert claims == ["Unopened equipment may be returned within 30 days."]


def test_decimal_money_retains_safe_summary_semantics():
    safe = pipeline._llm_safe_points([{"id":"total_revenue","raw_value":Decimal("30200.00")}], [])
    assert safe["metrics"] == [30200.0]
    assert safe["metric_context"] == [{"metric":"Gross revenue, all statuses","value":30200.0}]


CATALOG = {"invoices":{"columns":{"amount":"double","status":"str","_id":"id"}}}


@pytest.mark.parametrize("pipeline", [
    [{"$out":"stolen"}], [{"$merge":"invoices"}],
    [{"$match":{"$where":"return true"}}],
    [{"$project":{"x":{"$function":{"body":"return 1","args":[],"lang":"js"}}}}],
    [{"$lookup":{"from":"secrets","as":"data"}}],
    [{"$project":{"password":1}}],
    [{"$group":{"_id":None,"value":{"$sum":"$unknown"}}}],
    [{"$limit":100000}],
])
def test_mongo_read_plan_rejects_writes_code_sensitive_and_unknown_fields(pipeline):
    with pytest.raises(ValueError):
        validate_plan({"collection":"invoices","pipeline":pipeline}, CATALOG)


def test_mongo_read_plan_enforces_collection_publication_and_valid_aggregate():
    query={"collection":"invoices","pipeline":[{"$match":{"status":"paid"}},
           {"$group":{"_id":None,"paid_amount":{"$sum":"$amount"}}}]}
    assert validate_plan(query,CATALOG,["invoices"]).collection == "invoices"
    with pytest.raises(ValueError):
        validate_plan(query,CATALOG,["customers"])
    with pytest.raises(ValueError):
        validate_plan({**query,"collection":"system.users"})


@pytest.mark.parametrize('bson_type',['date','datetime'])
def test_mongo_dates_bind_only_catalog_date_fields(bson_type):
    from datetime import datetime
    original=[{'$match':{'created_at':{'$gte':'2026-10-01'},'label':'2026-10-01'}}]
    bound=bind_date_filters(original,{'created_at':[bson_type],'label':['string']})
    assert isinstance(bound[0]['$match']['created_at']['$gte'],datetime)
    assert bound[0]['$match']['label']=='2026-10-01'
    assert original[0]['$match']['created_at']['$gte']=='2026-10-01'


@pytest.fixture
def scoped_orders(isolated_db,tmp_path,monkeypatch):
    path=tmp_path/'scoped.sqlite'
    with sqlite3.connect(path) as source:
        source.executescript('''
        CREATE TABLE customers(id INTEGER PRIMARY KEY, customer_name TEXT);
        CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), total_amount REAL, region TEXT, order_date TEXT, status TEXT);
        CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id), quantity INTEGER);
        INSERT INTO customers VALUES(1,'Synthetic A'),(2,'Synthetic B');
        INSERT INTO orders VALUES(10,1,40,'East','2026-10-01','delivered'),(20,2,60,'West','2026-09-01','pending');
        INSERT INTO order_items VALUES(100,10,4),(200,20,6);
        ''')
    engine=create_engine(f'sqlite:///{path}')
    monkeypatch.setattr(db_utils,'get_connection_url',lambda _:engine.url)
    monkeypatch.setattr(db_pool,'get_engine',lambda _:engine)
    monkeypatch.setattr(pipeline,'cache_get',lambda _:None)
    monkeypatch.setattr(pipeline,'cache_set',lambda *a,**k:None)
    monkeypatch.setattr('services.llm_generation_service.generate',lambda *a,**k:(_ for _ in ()).throw(TimeoutError()))
    tenant=models.Tenant(name='Scoped synthetic tenant'); isolated_db.add(tenant); isolated_db.flush()
    connection=models.DatabaseConnection(name='Scoped synthetic source',tenant_id=tenant.id,db_type='sqlite',database=str(path))
    isolated_db.add(connection); isolated_db.flush()
    yield isolated_db,connection
    engine.dispose()


@pytest.mark.parametrize('filters',[{'filter_column':'orders.region','filter_value':'East'}, {'date_from':'2026-10-01','date_to':'2026-10-31'}])
def test_scoped_population_and_units_follow_verified_fact_relationship(scoped_orders,filters):
    db,connection=scoped_orders
    result=pipeline.DatabasePipelineService().run_db_pipeline(db,connection.id,tenant_id=connection.tenant_id,**filters)
    metrics={m['id']:m for m in result['key_metrics']}
    assert metrics['total_revenue']['raw_value']==40
    assert metrics['active_customers']['raw_value']==1
    assert metrics['units_sold']['raw_value']==4
    assert metrics['customer_lifetime_value']['raw_value']==40
    assert 'Insufficient' not in result['executive_summary']['executive_summary']


def test_missing_selected_table_does_not_substitute_another_source(scoped_orders):
    db,connection=scoped_orders
    with pytest.raises(ValueError,match='Selected table'):
        pipeline.DatabasePipelineService().run_db_pipeline(db,connection.id,tenant_id=connection.tenant_id,selected_table='does_not_exist')


def test_dimension_request_does_not_reuse_unfiltered_l2_payload(scoped_orders):
    db,connection=scoped_orders
    service=pipeline.DatabasePipelineService()
    service.run_db_pipeline(db,connection.id,tenant_id=connection.tenant_id)
    db.expire_all()
    result=service.run_db_pipeline(db,connection.id,tenant_id=connection.tenant_id,
                                   filter_column='orders.region',filter_value='East')
    assert next(m for m in result['key_metrics'] if m['id']=='total_revenue')['raw_value']==40


def test_stream_outage_before_first_token_persists_honest_fallback():
    from services.chat_stream import stream_chat_response
    saved=[]
    class Gateway:
        async def generate_stream(self,**kwargs):
            raise ConnectionError('synthetic provider outage')
            yield ''
    async def disconnected():
        return False
    fallback='AI synthesis is temporarily unavailable; no answer has been verified.'
    async def run():
        return [event async for event in stream_chat_response(
            request=SimpleNamespace(is_disconnected=disconnected),conversation_id=1,
            user_query='Unknown conversion rate?',prompt='Evidence',tenant_id=1,
            gateway=Gateway(),static_fallback=fallback,on_complete=lambda text:saved.append(text))]
    events=asyncio.run(run())
    payloads=[json.loads(event[6:]) for event in events]
    assert payloads[0]['chunk']==fallback
    assert payloads[-1]['done'] is True
    assert saved==[fallback]
