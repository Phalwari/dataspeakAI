from pathlib import Path

source = Path(r"D:/dataspeakAI/tests/manual/provision_demo_sources.py")
code = source.read_text(encoding="utf-8")
code = code.replace(
    'pg_bin = Path("C:/Program Files/PostgreSQL/18/bin")',
    'pg_bin = Path(r"D:/dataspeakAI/_qa_tmp/demo-runtime/postgresql/pgsql/bin")',
)
exec(compile(code, str(source), "exec"), {"__name__": "__main__", "__file__": str(source)})
