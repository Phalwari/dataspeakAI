"""Provision isolated, loopback-only demo servers and deterministic business data.

Requires official server ZIPs under the ignored _qa_tmp/demo-runtime directory.
Never connects to, resets, or drops an existing external database. Credentials
are randomly generated and kept in that ignored local runtime directory.
"""
from __future__ import annotations

import json
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Numeric, String, Table, create_engine, text
from sqlalchemy.engine import URL
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "_qa_tmp/demo-runtime"


def run(args):
    subprocess.run([str(x) for x in args], check=True, capture_output=True)


def start(args, name, port):
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(f"Refusing to reuse occupied demo port {port}")
    log = (RUNTIME / f"{name}-process.log").open("ab")
    proc = subprocess.Popen([str(x) for x in args], stdout=log, stderr=log,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    log.close()
    for _ in range(120):
        if proc.poll() is not None:
            raise RuntimeError(f"{name} exited; inspect local process log")
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                print(f"{name} listening on loopback:{port}", flush=True)
                return proc.pid
        time.sleep(1)
    raise TimeoutError(f"{name} startup exceeded 120 seconds")


def relational_fixture(engine, scenario):
    meta = MetaData()
    customers = Table("customers", meta, Column("id", Integer, primary_key=True),
                      Column("customer_name", String(80)), Column("region", String(40)))
    products = Table("products", meta, Column("id", Integer, primary_key=True),
                     Column("product_name", String(80)), Column("category", String(40)),
                     Column("unit_price", Numeric(12, 2)), Column("cost_price", Numeric(12, 2)))
    orders = Table("orders", meta, Column("id", Integer, primary_key=True),
                   Column("customer_id", Integer, ForeignKey("customers.id")),
                   Column("order_date", DateTime), Column("status", String(30)),
                   Column("total_amount", Numeric(12, 2)), Column("region", String(40)))
    lines = Table("order_items", meta, Column("id", Integer, primary_key=True),
                  Column("order_id", Integer, ForeignKey("orders.id")),
                  Column("product_id", Integer, ForeignKey("products.id")),
                  Column("quantity", Integer), Column("unit_price", Numeric(12, 2)),
                  Column("line_total", Numeric(12, 2)))
    meta.create_all(engine)
    count = 240 if scenario == "retail" else 180
    names = (["Espresso Maker", "Burr Grinder", "Coffee Beans", "Travel Mug", "Filter Kit", "Milk Frother"]
             if scenario == "retail" else ["Solar Panel", "Inverter", "Battery Pack", "Charge Controller", "Mounting Kit", "Cable Kit"])
    prices = [120, 80, 20, 25, 15, 40] if scenario == "retail" else [250, 400, 600, 125, 75, 30]
    product_rows = [dict(id=i+1, product_name=n, category="Equipment" if i < 3 else "Accessories",
                         unit_price=prices[i], cost_price=prices[i] * 0.6) for i, n in enumerate(names)]
    customer_rows = [dict(id=i, customer_name=f"Demo Customer {i:02}", region=["North", "South", "East", "West"][(i-1) % 4]) for i in range(1, 25)]
    order_rows, line_rows = [], []
    for i in range(1, count+1):
        product = product_rows[(i-1) % 6]
        qty = 1 + (i % 4)
        # Distinct September/October cohorts support hand-computed date comparisons.
        date = datetime(2026, 9, 1) + timedelta(days=(i-1) % 50)
        amount = int(product["unit_price"]) * qty
        status = "cancelled" if i % 10 == 0 else "pending" if i % 7 == 0 else "delivered"
        order_rows.append(dict(id=i, customer_id=1+(i-1) % 24, order_date=date, status=status,
                               total_amount=amount, region=customer_rows[(i-1) % 24]["region"]))
        line_rows.append(dict(id=i, order_id=i, product_id=product["id"], quantity=qty,
                              unit_price=product["unit_price"], line_total=amount))
    with engine.begin() as conn:
        for table, rows in [(customers, customer_rows), (products, product_rows), (orders, order_rows), (lines, line_rows)]:
            conn.execute(table.insert(), rows)
    def totals(rows):
        return {"orders": len(rows), "gross_revenue": sum(x["total_amount"] for x in rows),
                "delivered_revenue": sum(x["total_amount"] for x in rows if x["status"] == "delivered"),
                "cancelled_orders": sum(x["status"] == "cancelled" for x in rows),
                "pending_orders": sum(x["status"] == "pending" for x in rows)}
    return {"all": totals(order_rows), "october": totals([x for x in order_rows if x["order_date"].month == 10]),
            "customers": 24, "products": 6,
            "top_products": sorted([{ "product": p["product_name"], "revenue": sum(x["line_total"] for x in line_rows if x["product_id"] == p["id"])} for p in product_rows], key=lambda x: -x["revenue"])}


def main():
    if (RUNTIME / "sources.json").exists():
        raise RuntimeError("Demo runtime already provisioned; refusing to reseed")
    password = secrets.token_urlsafe(24)
    pg_bin = Path("C:/Program Files/PostgreSQL/18/bin")
    mysql_bin = next((RUNTIME / "mysql").glob("*/bin"))
    mongo_bin = next((RUNTIME / "mongo").glob("*/bin"))
    password_file = RUNTIME / "pg-password.txt"
    password_file.write_text(password)
    run([pg_bin / "initdb.exe", "-D", RUNTIME / "pg-data", "-U", "demo_admin", "--pwfile", password_file, "--auth=scram-sha-256", "--encoding=UTF8", "--no-locale"])
    pids = {"postgresql": start([pg_bin / "postgres.exe", "-D", RUNTIME / "pg-data", "-h", "127.0.0.1", "-p", "55432"], "postgresql", 55432)}
    pg_admin = create_engine(URL.create("postgresql+psycopg2", username="demo_admin", password=password, host="127.0.0.1", port=55432, database="postgres"), isolation_level="AUTOCOMMIT")
    with pg_admin.connect() as conn:
        conn.execute(text("CREATE DATABASE demo_coffee_retail"))
    pg_admin.dispose()
    run([mysql_bin / "mysqld.exe", "--no-defaults", "--initialize-insecure", f"--basedir={mysql_bin.parent}", f"--datadir={RUNTIME / 'mysql-data'}"])
    pids["mysql"] = start([mysql_bin / "mysqld.exe", "--no-defaults", f"--basedir={mysql_bin.parent}", f"--datadir={RUNTIME / 'mysql-data'}", "--bind-address=127.0.0.1", "--port=53306", "--mysqlx=OFF", "--console"], "mysql", 53306)
    import pymysql
    conn = pymysql.connect(host="127.0.0.1", port=53306, user="root", password="", autocommit=True)
    with conn.cursor() as cursor:
        cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (password,))
        cursor.execute("CREATE DATABASE demo_solar_wholesale")
    conn.close()
    (RUNTIME / "mongo-data").mkdir(exist_ok=True)
    pids["mongodb"] = start([mongo_bin / "mongod.exe", "--dbpath", RUNTIME / "mongo-data", "--bind_ip", "127.0.0.1", "--port", "57017", "--auth"], "mongodb", 57017)
    mongo = MongoClient("mongodb://127.0.0.1:57017", serverSelectionTimeoutMS=10000)
    mongo.admin.command("createUser", "demo_admin", pwd=password, roles=[{"role":"root", "db":"admin"}])
    mongo.close()
    mongo = MongoClient(host="127.0.0.1", port=57017, username="demo_admin", password=password, authSource="admin")
    mdb = mongo.demo_subscription_billing
    docs = []
    for i in range(1, 161):
        amount = [29, 79, 199][(i-1) % 3]
        docs.append({"invoice_id":i, "customer_id":1+(i-1) % 32, "plan":["Starter","Growth","Enterprise"][(i-1) % 3],
                     "amount":amount, "status":"cancelled" if i % 10 == 0 else "paid", "created_at":datetime(2026,9,1)+timedelta(days=(i-1)%50),
                     "customer":{"region":["North","South","East","West"][(i-1)%4]}, "currency":"USD"})
    mdb.invoices.insert_many(docs)
    mdb.customers.insert_many([{"customer_id":i,"company_name":f"Demo Business {i:02}","segment":"SMB" if i <=24 else "Enterprise"} for i in range(1,33)])
    mdb.support_tickets.insert_many([{"ticket_id":i,"customer_id":1+(i-1)%32,"priority":"high" if i%5==0 else "normal","status":"open" if i%4==0 else "resolved","resolution_hours":i%12+1,"created_at":datetime(2026,10,1)+timedelta(days=i%20)} for i in range(1,81)])
    sources = [dict(name="Demo | Coffee Retail | PostgreSQL",db_type="postgresql",host="127.0.0.1",port=55432,username="demo_admin",password=password,database="demo_coffee_retail",description="Synthetic coffee retailer; 240 orders; September–October 2026; USD."),
               dict(name="Demo | Solar Wholesale | MySQL",db_type="mysql",host="127.0.0.1",port=53306,username="root",password=password,database="demo_solar_wholesale",description="Synthetic solar wholesaler; 180 orders; September–October 2026; USD."),
               dict(name="Demo | Subscription Billing | MongoDB",db_type="mongodb",host="127.0.0.1",port=57017,username="demo_admin",password=password,database="demo_subscription_billing",connection_string=f"mongodb://demo_admin:{password}@127.0.0.1:57017/demo_subscription_billing?authSource=admin",description="Synthetic SaaS billing; 160 invoices, 32 customers, 80 support tickets; USD.")]
    truth = {}
    for source, scenario in zip(sources[:2], ["retail","wholesale"]):
        engine = create_engine(URL.create("postgresql+psycopg2" if source["db_type"] == "postgresql" else "mysql+pymysql",username=source["username"],password=password,host=source["host"],port=source["port"],database=source["database"]))
        truth[source["db_type"]] = relational_fixture(engine, scenario)
        engine.dispose()
    truth["mongodb"] = {"invoices":len(docs), "gross_billed":sum(x["amount"] for x in docs), "paid_revenue":sum(x["amount"] for x in docs if x["status"]=="paid"), "cancelled_invoices":16,"customers":32,"support_tickets":80,"open_tickets":20,
                        "october_gross_billed":sum(x["amount"] for x in docs if x["created_at"].month==10)}
    (RUNTIME / "sources.json").write_text(json.dumps(sources,indent=2))
    (RUNTIME / "pids.json").write_text(json.dumps(pids))
    (RUNTIME / "ground-truth.json").write_text(json.dumps(truth,indent=2))
    print(json.dumps(truth,indent=2), flush=True)


def start_existing():
    """Restart the existing demo data without reinitializing or reseeding it."""
    sources = json.loads((RUNTIME / "sources.json").read_text())
    mysql_bin = next((RUNTIME / "mysql").glob("*/bin"))
    mongo_bin = next((RUNTIME / "mongo").glob("*/bin"))
    commands = {
        "postgresql": ["C:/Program Files/PostgreSQL/18/bin/postgres.exe", "-D", RUNTIME / "pg-data", "-h", "127.0.0.1", "-p", "55432"],
        "mysql": [mysql_bin / "mysqld.exe", "--no-defaults", f"--basedir={mysql_bin.parent}", f"--datadir={RUNTIME / 'mysql-data'}", "--bind-address=127.0.0.1", "--port=53306", "--mysqlx=OFF", "--console"],
        "mongodb": [mongo_bin / "mongod.exe", "--dbpath", RUNTIME / "mongo-data", "--bind_ip", "127.0.0.1", "--port", "57017", "--auth"],
    }
    for source in sources:
        with socket.socket() as probe:
            running = probe.connect_ex(("127.0.0.1", source["port"])) == 0
        if not running:
            start(commands[source["db_type"]], source["db_type"], source["port"])
        print(source["db_type"], "listener ready", flush=True)


if __name__ == "__main__":
    start_existing() if "--start" in sys.argv else main()
