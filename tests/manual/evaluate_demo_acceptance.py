"""Evaluate captured live responses against independently generated fixture totals."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "_qa_tmp/demo-runtime"
OUTPUT = ROOT / "docs/reports/demo_qa_2026-10-21"


def load(name):
    return json.loads((RUNTIME / f"{name}.json").read_text())


def main():
    truth = load("ground-truth")
    checks = []
    evidence = {"ground_truth":truth, "chat":[], "insights":[], "streams":[]}

    def check(name, expected, actual):
        passed = actual == expected
        checks.append({"name":name,"passed":passed,"expected":expected,"actual":actual})
        print(f"{'PASS' if passed else 'FAIL'} {name}: {actual!r} (expected {expected!r})")

    for dialect in ("postgresql", "mysql"):
        for window in ("all", "october"):
            result = load(f"insights-{dialect}-{window}")
            body = result["body"]
            metrics = {m["id"]:m.get("raw_value") for m in body["key_metrics"]}
            for metric, key in [("total_revenue","gross_revenue"),("net_revenue_delivered","delivered_revenue"),("total_orders","orders")]:
                check(f"{dialect}/{window}/{metric}",truth[dialect][window][key],metrics.get(metric))
            evidence["insights"].append({"dialect":dialect,"window":window,"seconds":result["seconds"],"metrics":body["key_metrics"],"summary":body.get("executive_summary")})
    for window, count, amount in [("all",160,truth["mongodb"]["gross_billed"]),("october",60,truth["mongodb"]["october_gross_billed"])]:
        result=load(f"insights-mongodb-{window}"); body=result["body"]; metrics={m["id"]:m.get("raw_value") for m in body["key_metrics"]}
        check(f"mongodb/{window}/invoices",count,metrics.get("invoices_total_rows"))
        check(f"mongodb/{window}/gross_billed",amount,metrics.get("invoices_amount_sum"))
        evidence["insights"].append({"dialect":"mongodb","window":window,"seconds":result["seconds"],"metrics":body["key_metrics"],"summary":body.get("executive_summary")})
    for dialect in ("postgresql","mysql","mongodb"):
        body=load(f"insights-{dialect}-empty")["body"]
        count_id="invoices_total_rows" if dialect=="mongodb" else "total_orders"
        metrics={m["id"]:m for m in body["key_metrics"]}
        check(f"{dialect}/empty/count",0,metrics[count_id].get("raw_value"))
    for name, amount, field in [("pg_delivered",23695,"delivered_total_amount"),("pg_october",11255,"total_amount_sum"),("pg_join",14400,"revenue"),("mysql_delivered",94125,"delivered_total_amount")]:
        body=load("chat-"+name)["body"]; sql=body.get("sql_data") or {}; rows=sql.get("rows",[])
        actual=float(rows[0][field]) if rows and field in rows[0] else None
        check("chat/"+name,amount,actual)
    for name, expected in [("pg_total",30200),("mysql_total",116550)]:
        rows=load("chat-"+name)["body"]["sql_data"]["rows"]
        check("chat/"+name,expected,sum(float(row["total_amount_sum"]) for row in rows))
    for name in ("coffee","solar","orbit"):
        result=load("ready-rag-"+name)
        check("grounding/"+name,"supported",result["body"].get("grounding_status"))
    # Region East has six customers (IDs 3,7,11,15,19,23), each line quantity 4.
    regional=load("extra-region-east")["body"]
    regional_metrics={m["id"]:m.get("raw_value") for m in regional["key_metrics"]}
    check("region/East/revenue",12400,regional_metrics.get("total_revenue"))
    check("region/East/customers",6,regional_metrics.get("active_customers"))
    check("region/East/units",240,regional_metrics.get("units_sold"))
    check("invalid_table/rejected",True,load("extra-invalid-table")["status"] in (400,404,422))
    for name in ("sql","rag"):
        stream=load("stream-"+name); events=[json.loads(e["line"][6:]) for e in stream["events"] if e["line"].startswith("data: ")]
        check("stream/"+name+"/done",True,events[-1].get("done"))
        evidence["streams"].append({"name":name,"first_event_seconds":stream["events"][0]["seconds"],"completion_seconds":stream["events"][-1]["seconds"],"chunk_count":sum(bool(e.get("chunk")) for e in events),"done":events[-1]})
    for file in sorted(RUNTIME.glob("chat-*.json")):
        if file.name != "chat-results.json":
            evidence["chat"].append(json.loads(file.read_text()))
    for file in sorted(RUNTIME.glob("ready-*.json")):
        evidence["chat"].append(json.loads(file.read_text()))
    evidence["widget"] = widget = load("widget-results")
    check("widget/handshake",200,widget["handshake_status"])
    check("widget/unapproved_origin",403,widget["unapproved_origin_status"])
    check("widget/coffee_facts",True,all(value in widget["coffee"]["body"]["answer"] for value in ("30","100")))
    check("widget/orbit_fact",True,"1 business hour" in widget["orbit"]["body"]["answer"])
    for name in ("mongo_billing","mongo_paid"):
        check("chat/"+name+"/execution","success",(load("chat-"+name)["body"].get("sql_data") or {}).get("status"))
    evidence["filter_probe"] = regional
    evidence["invalid_table_probe"] = load("extra-invalid-table")
    evidence["mongo_retry"] = load("mongo-retry")
    evidence["auto_database_selection"] = load("auto-coffee")
    evidence["checks"] = checks
    evidence["check_summary"]={"passed":sum(x["passed"] for x in checks),"failed":sum(not x["passed"] for x in checks),"total":len(checks)}
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT/"evidence.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
    print(json.dumps(evidence["check_summary"]))


if __name__ == "__main__":
    main()
