"""Offline orchestration for existing suites; no test logic."""
import os
from pathlib import Path
import sys
import tempfile
if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parents[2]
    OUT = Path(__file__).resolve().parent
    WORK = Path(tempfile.mkdtemp(prefix="isolated-", dir=OUT))
    for key in list(os.environ):
        if any(tag in key.upper() for tag in ("API_KEY", "CLIENT_SECRET", "DATABASE_URL", "REDIS_URL", "CELERY", "RESEND", "SMTP")):
            os.environ.pop(key, None)
    os.environ.update({
        "DATABASE_URL": "sqlite:///" + (WORK / "app.db").as_posix(),
        "EMBEDDING_WARMUP": "false", "ENVIRONMENT": "test",
        "SECRET_KEY": "nr2-isolated-verification-secret-key-2026",
        "WIDGET_HMAC_SECRET": "nr2-isolated-widget-hmac-secret-key-2026",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHON_DOTENV_DISABLED": "1", "HF_HOME": os.environ.get("AUDIT_HF_HOME", str(WORK / "hf-cache")),
        "ENABLE_DEV_SEED": "false",
    })
    sys.dont_write_bytecode = True
    os.chdir(WORK)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "backend"))
    import dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: False
    import requests
    import httpx
    def deny_network(*args, **kwargs):
        raise RuntimeError("External network disabled during isolated verification")
    async def deny_async_network(*args, **kwargs):
        raise RuntimeError("External network disabled during isolated verification")
    requests.sessions.Session.request = deny_network
    httpx.HTTPTransport.handle_request = deny_network
    httpx.AsyncHTTPTransport.handle_async_request = deny_async_network
    import pytest
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    selected = sys.argv[2:]
    paths = selected or (["tests/manual/fyp_core_verification.py"] if mode == "manual" else ["tests"])
    print("Python:", sys.version.split()[0], "| mode:", mode, "| temporary storage:", WORK.name, flush=True)
    raise SystemExit(pytest.main([
        *[str(ROOT / path) for path in paths], "-q", "-p", "no:cacheprovider",
        "--tb=short", "--junitxml=" + str(OUT / (mode + "-results.xml")),
        "--disable-warnings", "--basetemp=" + str(WORK / "pytest"),
    ]))
