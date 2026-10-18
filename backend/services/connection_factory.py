"""
Database Connection Factory & SSRF Defense Service.
Implements Milestone NR-1.2 connection security:
- DNS resolution and SSRF defense (blocking RFC 1918, loopback, link-local, multicast)
- SQLite managed root validation and directory traversal prevention
- Type-safe SQLAlchemy URL.create assembly
- Dialect statement timeout options
- Safe credential resolution via crypto_service
"""
import ipaddress
import logging
import os
from pathlib import Path
import socket
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

from services.crypto_service import decrypt_secret, redact_connection_url

logger = logging.getLogger(__name__)

SUPPORTED_DIALECTS = {"postgresql", "mysql", "mariadb", "sqlite", "mongodb"}
DEFAULT_SQLITE_ROOT = Path("data/sqlite_dbs").resolve()


class SSRFSecurityViolation(ValueError):
    """Raised when a target host resolves to a forbidden internal or private network IP."""
    pass


class InvalidDatabasePathError(ValueError):
    """Raised when an external database path violates storage isolation or attempts directory traversal."""
    pass


class DatabaseConnectionFactory:
    """Centralized factory for validating, assembling, and provisioning external database connections."""

    @classmethod
    def allow_private_networks(cls) -> bool:
        """Checks if internal / private subnet connections are explicitly permitted."""
        return os.getenv("ALLOW_PRIVATE_DB_HOSTS", "").strip().lower() in ("true", "1", "yes")

    @classmethod
    def validate_host_ssrf(cls, host: str, port: Optional[int] = None) -> str:
        """Resolves target host and asserts it does not route to private/loopback/link-local addresses.
        
        Raises SSRFSecurityViolation if resolution hits blocked IP ranges.
        """
        if not host:
            raise ValueError("Host name or IP address is required.")
        
        host_clean = host.strip()
        port_num = port or 5432
        
        # Check direct IP string or resolve DNS
        try:
            addr_info = socket.getaddrinfo(host_clean, port_num, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            logger.warning("DNS resolution failed for host %s: %s", host_clean, exc)
            raise ValueError(f"Could not resolve host '{host_clean}'") from exc
        
        resolved_ips = set()
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            resolved_ips.add(ip_str)
        
        allow_private = cls.allow_private_networks()
        for ip_str in resolved_ips:
            ip = ipaddress.ip_address(ip_str)
            if not allow_private:
                if (
                    ip.is_loopback
                    or ip.is_private
                    or ip.is_link_local
                    or ip.is_multicast
                    or ip.is_reserved
                    or ip.is_unspecified
                ):
                    logger.warning("SSRF violation blocked: host '%s' resolved to prohibited IP %s", host_clean, ip_str)
                    raise SSRFSecurityViolation(
                        f"SSRF violation: Host '{host_clean}' resolves to private or internal IP ({ip_str}), "
                        "which is forbidden."
                    )
        
        return host_clean

    @classmethod
    def validate_sqlite_path(cls, database_path: str) -> Path:
        """Validates SQLite database path against the managed sandbox root, blocking directory traversal."""
        if not database_path:
            raise ValueError("Database path is required for SQLite connections.")
        
        if ".." in database_path:
            raise InvalidDatabasePathError("Directory traversal ('..') is strictly prohibited in SQLite database paths.")
        
        # Normalize and ensure root exists
        managed_root = DEFAULT_SQLITE_ROOT
        managed_root.mkdir(parents=True, exist_ok=True)
        
        raw_path = Path(database_path)
        if raw_path.is_absolute():
            resolved = raw_path.resolve()
        else:
            resolved = (managed_root / raw_path).resolve()
        
        try:
            resolved.relative_to(managed_root)
        except ValueError:
            raise InvalidDatabasePathError(
                f"SQLite path '{database_path}' is outside the managed sandbox root ({managed_root})."
            )
        
        if resolved.suffix.lower() not in (".db", ".sqlite", ".sqlite3"):
            raise InvalidDatabasePathError("SQLite files must have a valid extension (.db, .sqlite, .sqlite3).")
        
        return resolved

    @classmethod
    def build_connection_url(
        cls,
        db_type: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None,
    ) -> URL:
        """Constructs a type-safe SQLAlchemy URL object with dialect driver mappings."""
        dialect = db_type.lower()
        if dialect not in SUPPORTED_DIALECTS:
            raise ValueError(f"Unsupported database type '{db_type}'. Must be one of {SUPPORTED_DIALECTS}")
        
        # Decrypt password if stored in v1 envelope
        decrypted_password = decrypt_secret(password) if password else None
        
        if dialect == "sqlite":
            if not database:
                raise ValueError("Database file path is required for SQLite connections.")
            validated_path = cls.validate_sqlite_path(database)
            return URL.create(
                drivername="sqlite",
                database=validated_path.as_posix(),
                query=query_params or {},
            )
        
        # Network dialects: validate host SSRF
        validated_host = cls.validate_host_ssrf(host, port)
        
        driver_map = {
            "postgresql": "postgresql+psycopg2",
            "mysql": "mysql+pymysql",
            "mariadb": "mysql+pymysql",
            "mongodb": "mongodb",
        }
        drivername = driver_map[dialect]
        
        return URL.create(
            drivername=drivername,
            username=username,
            password=decrypted_password,
            host=validated_host,
            port=port,
            database=database,
            query=query_params or {},
        )

    @classmethod
    def create_engine_instance(
        cls,
        db_type: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None,
        statement_timeout_ms: int = 5000,
    ) -> Engine:
        """Creates a configured SQLAlchemy Engine instance with dialect-specific timeouts."""
        url = cls.build_connection_url(
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            query_params=query_params,
        )
        
        connect_args: Dict[str, Any] = {}
        dialect = db_type.lower()
        timeout_sec = max(1, int(statement_timeout_ms / 1000))
        
        if dialect == "postgresql":
            connect_args["options"] = f"-c statement_timeout={statement_timeout_ms}"
            connect_args["connect_timeout"] = timeout_sec
        elif dialect in ("mysql", "mariadb"):
            connect_args["connect_timeout"] = timeout_sec
        elif dialect == "sqlite":
            connect_args["timeout"] = float(timeout_sec)
        
        return create_engine(
            url,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_recycle=300,
        )

    @classmethod
    def test_connection(
        cls,
        db_type: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        statement_timeout_ms: int = 5000,
    ) -> Tuple[bool, Optional[str]]:
        """Tests external connection with statement timeouts and redacts credentials on failure."""
        dialect = db_type.lower()
        if dialect == "mongodb":
            # For MongoDB, verify pymongo if available
            try:
                from pymongo import MongoClient
                validated_host = cls.validate_host_ssrf(host, port)
                decrypted_pwd = decrypt_secret(password) if password else None
                client = MongoClient(
                    host=validated_host,
                    port=port or 27017,
                    username=username,
                    password=decrypted_pwd,
                    serverSelectionTimeoutMS=statement_timeout_ms,
                )
                client.admin.command("ping")
                client.close()
                return True, None
            except Exception as exc:
                err_msg = redact_connection_url(str(exc))
                return False, f"MongoDB connection failed: {err_msg}"
        
        try:
            engine = cls.create_engine_instance(
                db_type=db_type,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                statement_timeout_ms=statement_timeout_ms,
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return True, None
        except Exception as exc:
            err_msg = redact_connection_url(str(exc))
            logger.warning("Database connection test failed: %s", err_msg)
            return False, f"Connection failed: {err_msg}"
