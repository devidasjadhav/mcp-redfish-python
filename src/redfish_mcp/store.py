"""Shared, revisioned storage for learned Redfish contracts and write audits."""

import json
import sqlite3
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ContractConflictError(RuntimeError):
    """Raised when a contract compare-and-swap detects a concurrent update."""


class ContractStore(ABC):
    """Persistence interface used by the contract resolver."""

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Return a contract document or None."""

    @abstractmethod
    def put(self, key: str, document: Dict[str, Any], expected_revision: int) -> int:
        """Store a document and return its new monotonic revision."""

    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Delete a contract while retaining its audit records."""

    @abstractmethod
    def append_audit(self, record: Dict[str, Any]) -> str:
        """Append an audit record and return its identifier."""

    @abstractmethod
    def list_audits(self, key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return audit records, optionally limited to a contract key."""


class SQLiteContractStore(ContractStore):
    """SQLite-backed store suitable for processes sharing one filesystem."""

    def __init__(self, path: str):
        """Initialize the schema.

        Args:
            path: SQLite database path.
        """
        self.path = path
        self._lock = threading.RLock()
        self._memory_connection: Optional[sqlite3.Connection] = None
        if path == ":memory:":
            self._memory_connection = sqlite3.connect(path, check_same_thread=False)
            self._memory_connection.row_factory = sqlite3.Row
        if path != ":memory:":
            Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        if self._memory_connection is not None:
            return self._memory_connection
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS contracts (
                    contract_key TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    document TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audits (
                    audit_id TEXT PRIMARY KEY,
                    contract_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS contract_counters (
                    contract_key TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS audits_contract_key "
                "ON audits(contract_key, created_at)"
            )

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT revision, document FROM contracts WHERE contract_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        document = json.loads(row["document"])
        document["revision"] = row["revision"]
        return document

    def put(self, key: str, document: Dict[str, Any], expected_revision: int) -> int:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision FROM contracts WHERE contract_key = ?",
                (key,),
            ).fetchone()
            current_revision = int(row["revision"]) if row else 0
            if current_revision != expected_revision:
                connection.rollback()
                raise ContractConflictError(
                    f"Expected revision {expected_revision}, found {current_revision}"
                )
            counter_row = connection.execute(
                "SELECT revision FROM contract_counters WHERE contract_key = ?",
                (key,),
            ).fetchone()
            last_revision = int(counter_row["revision"]) if counter_row else 0
            revision = last_revision + 1
            stored = dict(document)
            stored["revision"] = revision
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                """
                INSERT INTO contracts(contract_key, revision, document, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(contract_key) DO UPDATE SET
                    revision = excluded.revision,
                    document = excluded.document,
                    updated_at = excluded.updated_at
                """,
                (key, revision, json.dumps(stored, sort_keys=True), now),
            )
            connection.execute(
                """
                INSERT INTO contract_counters(contract_key, revision)
                VALUES (?, ?)
                ON CONFLICT(contract_key) DO UPDATE SET revision = excluded.revision
                """,
                (key, revision),
            )
            connection.commit()
            return revision

    def invalidate(self, key: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM contracts WHERE contract_key = ?",
                (key,),
            )

    def append_audit(self, record: Dict[str, Any]) -> str:
        audit_id = str(record.get("audit_id") or uuid.uuid4())
        stored = dict(record)
        stored["audit_id"] = audit_id
        stored.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        key = str(stored["contract_key"])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audits(audit_id, contract_key, created_at, record) "
                "VALUES (?, ?, ?, ?)",
                (audit_id, key, stored["timestamp"], json.dumps(stored, sort_keys=True)),
            )
        return audit_id

    def list_audits(self, key: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            if key is None:
                rows = connection.execute(
                    "SELECT record FROM audits ORDER BY created_at"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT record FROM audits WHERE contract_key = ? ORDER BY created_at",
                    (key,),
                ).fetchall()
        return [json.loads(row["record"]) for row in rows]


class RedisContractStore(ContractStore):
    """Redis-backed contract store for instances on different hosts."""

    _PUT_SCRIPT = """
local raw = redis.call('GET', KEYS[1])
local current = 0
if raw then
  local decoded = cjson.decode(raw)
  current = tonumber(decoded.revision)
end
if current ~= tonumber(ARGV[1]) then
  return -1
end
local counter = tonumber(redis.call('GET', KEYS[2]) or '0')
if counter < current then
  redis.call('SET', KEYS[2], current)
end
local document = cjson.decode(ARGV[2])
local revision = redis.call('INCR', KEYS[2])
document.revision = revision
redis.call('SET', KEYS[1], cjson.encode(document))
return revision
"""

    def __init__(self, url: str):
        """Connect to Redis and verify the configured endpoint."""
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("REDIS_URL requires the 'redis' package") from exc
        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._redis.ping()

    @staticmethod
    def _contract_key(key: str) -> str:
        return f"redfish:contract:{key}"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        raw = self._redis.get(self._contract_key(key))
        return json.loads(raw) if raw else None

    def put(self, key: str, document: Dict[str, Any], expected_revision: int) -> int:
        # This executes the fixed Lua script above in Redis; no user-supplied code
        # is evaluated. The script makes revision compare-and-swap atomic.
        revision = int(
            self._redis.eval(
                self._PUT_SCRIPT,
                2,
                self._contract_key(key),
                f"redfish:contract-revision:{key}",
                expected_revision,
                json.dumps(document, sort_keys=True),
            )
        )
        if revision < 0:
            raise ContractConflictError("Contract changed during exploration")
        return revision

    def invalidate(self, key: str) -> None:
        self._redis.delete(self._contract_key(key))

    def append_audit(self, record: Dict[str, Any]) -> str:
        audit_id = str(record.get("audit_id") or uuid.uuid4())
        stored = dict(record)
        stored["audit_id"] = audit_id
        stored.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        key = str(stored["contract_key"])
        pipe = self._redis.pipeline()
        pipe.set(f"redfish:audit:{audit_id}", json.dumps(stored, sort_keys=True))
        pipe.rpush(f"redfish:audits:{key}", audit_id)
        pipe.execute()
        return audit_id

    def list_audits(self, key: Optional[str] = None) -> List[Dict[str, Any]]:
        if key is None:
            audit_keys = self._redis.scan_iter("redfish:audit:*")
            records = [json.loads(value) for value in self._redis.mget(list(audit_keys)) if value]
            return sorted(records, key=lambda item: item["timestamp"])
        identifiers = self._redis.lrange(f"redfish:audits:{key}", 0, -1)
        if not identifiers:
            return []
        values = self._redis.mget([f"redfish:audit:{item}" for item in identifiers])
        return [json.loads(value) for value in values if value]


def create_contract_store(
    sqlite_path: str,
    redis_url: Optional[str] = None,
) -> ContractStore:
    """Create the configured shared contract store."""
    if redis_url:
        return RedisContractStore(redis_url)
    return SQLiteContractStore(sqlite_path)
