from sqlalchemy import create_engine
import threading

_engine_cache = {}
_lock = threading.Lock()

def get_engine(url: str):
    with _lock:
        if url not in _engine_cache:
            # Using pool settings suitable for standard SQLAlchemy operations
            # Note: For SQLite, pool options might need adjustment depending on connect string
            kwargs = {}
            if not url.startswith("sqlite"):
                kwargs = {
                    "pool_size": 5, 
                    "max_overflow": 5,
                    "pool_timeout": 10, 
                    "pool_pre_ping": True, 
                    "pool_recycle": 1800
                }
            else:
                kwargs = {
                    "pool_pre_ping": True,
                    "pool_recycle": 1800
                }
            
            _engine_cache[url] = create_engine(url, **kwargs)
        return _engine_cache[url]
