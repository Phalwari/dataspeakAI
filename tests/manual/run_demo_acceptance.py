"""Live, authenticated demo QA. Reports observed responses without mocking providers.

Run after provision_demo_sources.py. Session and evidence stay in ignored local
runtime files. Pass setup, chat, insights, or inspect as the first argument.
"""
import concurrent.futures
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "_qa_tmp/demo-runtime"
BASE = "http://127.0.0.1:8000"


def request(method, path, **kwargs):
    session = json.loads((RUNTIME / "session.json").read_text())
    headers = {"Authorization": "Bearer " + session["access_token"]}
    started = time.monotonic()
    response = requests.request(method, BASE + path, headers=headers, timeout=180, **kwargs)
    try:
        body = response.json()
    except ValueError:
        body = response.text
    return {"status": response.status_code, "seconds": round(time.monotonic()-started, 2), "body": body}


def setup():
    sources = json.loads((RUNTIME / "sources.json").read_text())
    evidence = []
    for source in sources:
        result = request("POST", "/api/databases/test", json=source)
        evidence.append({"name":source["name"], "test":result})
        print(source["db_type"], "connection test", result, flush=True)
        if result["status"] != 200:
            continue
        result = request("POST", "/api/databases", json=source)
        if result["status"] != 200:
            raise RuntimeError(result)
        source["id"] = result["body"]["id"]
        tables = request("GET", f"/api/databases/{source['id']}/tables")
        evidence[-1]["tables"] = tables
        print(source["db_type"], "registered", source["id"], "tables", tables, flush=True)
    (RUNTIME / "sources.json").write_text(json.dumps(sources, indent=2))
    for path in sorted((ROOT / "tests/fixtures/demo_business").glob("*.txt")):
        with path.open("rb") as file:
            result = request("POST", "/api/documents/upload", files={"file":(path.name,file,"text/plain")}, data={"chunk_size":1000,"chunk_overlap":150})
        evidence.append({"document":path.name,"upload":result})
        print("uploaded",path.name,result["status"],flush=True)
    (RUNTIME / "setup-results.json").write_text(json.dumps(evidence,indent=2))


def chat():
    ids = {s["db_type"]:s["id"] for s in json.loads((RUNTIME/"sources.json").read_text()) if "id" in s}
    cases = [
        ("pg_total", "database", "postgresql", "How many orders are there and what is the sum of total_amount across all order statuses?", {"orders":240,"gross":30200}),
        ("pg_delivered", "database", "postgresql", "What is the sum of total_amount for orders with status delivered only?", {"delivered":23695}),
        ("pg_october", "database", "postgresql", "For October 2026 only, how many orders are there and what is total_amount across all statuses?", {"orders":90,"gross":11255}),
        ("pg_join", "database", "postgresql", "Which product has the highest total order_items.line_total across all statuses? Join products using product_id and return its name and revenue.", {"product":"Espresso Maker","revenue":14400}),
        ("mysql_total", "database", "mysql", "How many orders are there and what is the sum of total_amount across all order statuses?", {"orders":180,"gross":116550}),
        ("mysql_delivered", "database", "mysql", "What is the sum of total_amount for orders with status delivered only?", {"delivered":94125}),
        ("mongo_billing", "database", "mongodb", "How many invoices are there and what is their total amount across all statuses?", {"invoices":160,"gross":16300}),
        ("mongo_paid", "database", "mongodb", "What is the total invoice amount for invoices whose status is paid?", {"paid":14736}),
        ("coffee_policy", "documents", None, "According to Harbor Coffee Retail policy, how many days do I have to return unopened equipment and what is the free standard shipping minimum?", {"return_days":30,"minimum":100}),
        ("solar_policy", "documents", None, "According to Sunridge Solar Wholesale policy, what are payment terms and the inverter warranty duration?", {"net_days":45,"warranty_years":5}),
        ("orbit_policy", "documents", None, "According to Orbit Subscriptions guide, what is the high-priority first-response target and support escalation code?", {"hours":1,"code":"ORBIT-SLA-81"}),
        ("unknown_fact", "documents", None, "What exact loyalty points conversion rate does Harbor Coffee Retail offer?", {"expected":"Explicitly state that the policy does not specify it"}),
        ("forecast_limit", "auto", "postgresql", "What is our guaranteed coffee retail revenue for 2027?", {"expected":"No guaranteed forecast can be established"}),
        ("greeting", "auto", None, "Hi, what can you help me do with my data?", {"expected":"Conversational platform help"}),
    ]
    def execute(case):
        name, preference, dialect, query, expected = case
        payload = {"query":query,"source_preference":preference,"stream":False}
        if dialect:
            payload["database_id"] = ids[dialect]
        try:
            result = request("POST", "/api/chat", json=payload)
        except Exception as error:
            result = {"error":type(error).__name__,"detail":str(error)}
        result.update(name=name,query=query,expected=expected)
        (RUNTIME / f"chat-{name}.json").write_text(json.dumps(result,indent=2))
        print(name,json.dumps(result),flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(execute,cases))
    (RUNTIME/"chat-results.json").write_text(json.dumps(results,indent=2))
    # Follow-up must remain attached to its original conversation.
    first = next(r for r in results if r["name"] == "pg_total")
    if first.get("body",{}).get("conversation_id"):
        followup = request("POST","/api/chat",json={"query":"Now only delivered orders, please.","conversation_id":first["body"]["conversation_id"],"source_preference":"auto"})
        (RUNTIME/"chat-followup.json").write_text(json.dumps(followup,indent=2))
        print("followup",json.dumps(followup),flush=True)


def insights():
    sources = json.loads((RUNTIME/"sources.json").read_text())
    results=[]
    for source in sources:
        if "id" not in source:
            continue
        for name, params in [("all",{"refresh":"true"}), ("october",{"refresh":"true","date_from":"2026-10-01","date_to":"2026-10-31"}), ("empty",{"refresh":"true","date_from":"2027-01-01","date_to":"2027-01-31"})]:
            try:
                result=request("GET",f"/api/insights/generate/{source['id']}",params=params)
            except Exception as error:
                result={"error":type(error).__name__,"detail":str(error)}
            result.update(dialect=source["db_type"],window=name)
            results.append(result)
            (RUNTIME/f"insights-{source['db_type']}-{name}.json").write_text(json.dumps(result,indent=2))
            print(source["db_type"],name,json.dumps(result),flush=True)
    (RUNTIME/"insights-results.json").write_text(json.dumps(results,indent=2))


if __name__ == "__main__":
    {"setup":setup,"chat":chat,"insights":insights,"inspect":lambda:print(json.dumps(request("GET","/api/documents"),indent=2))}[sys.argv[1]]()
