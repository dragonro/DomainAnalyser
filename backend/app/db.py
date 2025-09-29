from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import DomainAnalysisResponse

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "domain_analyser.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS domain_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                looked_up_at TEXT NOT NULL,
                domain_exists INTEGER NOT NULL,
                apex_records TEXT NOT NULL,
                providers TEXT NOT NULL,
                subdomains TEXT NOT NULL,
                networks TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        columns = {info[1] for info in conn.execute("PRAGMA table_info(domain_reports)")}
        if "networks" not in columns:
            conn.execute("ALTER TABLE domain_reports ADD COLUMN networks TEXT NOT NULL DEFAULT '[]'")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_domain_reports_domain
            ON domain_reports(domain)
            """
        )


def save_analysis(analysis: DomainAnalysisResponse, looked_up_at: str) -> None:
    payload = {
        "domain": analysis.domain,
        "looked_up_at": looked_up_at,
        "domain_exists": 1 if analysis.exists else 0,
        "apex_records": json.dumps(analysis.apex_records),
        "providers": json.dumps(analysis.providers.model_dump()),
        "subdomains": json.dumps([item.model_dump() for item in analysis.subdomains]),
        "networks": json.dumps(analysis.networks),
    }

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO domain_reports (domain, looked_up_at, domain_exists, apex_records, providers, subdomains, networks)
            VALUES (:domain, :looked_up_at, :domain_exists, :apex_records, :providers, :subdomains, :networks)
            """,
            payload,
        )


def fetch_recent_reports(limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, domain, looked_up_at, domain_exists, apex_records, providers, subdomains, networks
            FROM domain_reports
            ORDER BY looked_up_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "id": row["id"],
                "domain": row["domain"],
                "looked_up_at": row["looked_up_at"],
                "exists": bool(row["domain_exists"]),
                "apex_records": json.loads(row["apex_records"]),
                "providers": json.loads(row["providers"]),
                "subdomains": json.loads(row["subdomains"]),
                "networks": json.loads(row["networks"] or "[]"),
            }
        )
    return results


def fetch_report_by_domain(domain: str) -> Dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, domain, looked_up_at, domain_exists, apex_records, providers, subdomains, networks
            FROM domain_reports
            WHERE domain = ?
            ORDER BY looked_up_at DESC
            LIMIT 1
            """,
            (domain,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "domain": row["domain"],
        "looked_up_at": row["looked_up_at"],
        "exists": bool(row["domain_exists"]),
        "apex_records": json.loads(row["apex_records"]),
        "providers": json.loads(row["providers"]),
        "subdomains": json.loads(row["subdomains"]),
        "networks": json.loads(row["networks"] or "[]"),
    }
