from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response

from . import db
from .models import (
    DomainAnalysisResponse,
    DomainLookupRequest,
    DomainLookupResponse,
    ProviderBreakdown,
    StoredReport,
    SubdomainInsight,
)
from .services import dns_service

app = FastAPI(title="Domain Analyzer API", version="0.1.0")

FRONTEND_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


@app.on_event("startup")
async def startup() -> None:
    db.init_db()


def _frontend_file(filename: str) -> pathlib.Path:
    path = FRONTEND_ROOT / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found")
    return path


@app.get("/", include_in_schema=False)
async def serve_index() -> FileResponse:
    return FileResponse(_frontend_file("index.html"))


@app.get("/{page}.html", include_in_schema=False)
async def serve_frontend_page(page: str) -> FileResponse:
    allowed_pages = {"insight", "report"}
    if page not in allowed_pages:
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(_frontend_file(f"{page}.html"))


@app.get("/app-config.js", include_in_schema=False)
async def serve_app_config() -> Response:
    script_lines = [
        "(function() {",
        '  const apiBase = window.location.origin;',
        '  window.APP_CONFIG = { apiBase };',
        '  window.appApiUrl = function(path = "") {',
        '    if (!path) {',
        '      return apiBase;',
        '    }',
        '    const normalized = path.startsWith("/") ? path : `/${path}`;',
        '    return `${apiBase}${normalized}`;',
        '  };',
        '})();',
    ]
    script = "\n".join(script_lines)
    return Response(content=script, media_type="application/javascript")


@app.post("/api/lookup", response_model=DomainLookupResponse)
async def lookup_domain(request: DomainLookupRequest) -> DomainLookupResponse:
    domain = request.domain.lower()
    exists = await dns_service.verify_domain(domain)
    message = "Domain verified." if exists else "We could not verify this domain."
    return DomainLookupResponse(domain=domain, exists=exists, message=message)


@app.get("/api/domains/{domain}", response_model=DomainAnalysisResponse)
async def get_domain_analysis(
    domain: str,
    include_subdomains: bool = Query(True),
    wordlist: str | None = Query(None),
    max_concurrency: int = Query(20, ge=1, le=100),
) -> DomainAnalysisResponse:
    domain = domain.lower()
    wordlist_path = pathlib.Path(wordlist) if wordlist else None
    analysis = await dns_service.analyze_domain(
        domain,
        include_subdomains=include_subdomains,
        wordlist=wordlist_path,
        max_concurrency=max_concurrency,
    )
    if not analysis.exists:
        raise HTTPException(status_code=404, detail="Domain not found")
    db.save_analysis(analysis, datetime.utcnow().isoformat())
    return analysis


def _build_subdomain_insights(records: List[dict]) -> List[SubdomainInsight]:
    insights: List[SubdomainInsight] = []
    for item in records:
        provider = ProviderBreakdown.model_validate(item["providers"])
        insights.append(
            SubdomainInsight(
                fqdn=item["fqdn"],
                records=item["records"],
                providers=provider,
                networks=item.get("networks", []),
            )
        )
    return insights


def _build_domain_analysis(row: dict) -> DomainAnalysisResponse:
    return DomainAnalysisResponse(
        domain=row["domain"],
        exists=row["exists"],
        apex_records=row["apex_records"],
        providers=ProviderBreakdown.model_validate(row["providers"]),
        subdomains=_build_subdomain_insights(row["subdomains"]),
        networks=row.get("networks", []),
    )


def _build_stored_report(row: dict) -> StoredReport:
    return StoredReport(
        id=row["id"],
        domain=row["domain"],
        looked_up_at=row["looked_up_at"],
        exists=row["exists"],
        apex_records=row["apex_records"],
        providers=ProviderBreakdown.model_validate(row["providers"]),
        subdomains=_build_subdomain_insights(row["subdomains"]),
        networks=row.get("networks", []),
    )


@app.get("/api/reports", response_model=List[StoredReport])
async def list_reports(limit: int = Query(20, ge=1, le=100)) -> List[StoredReport]:
    rows = db.fetch_recent_reports(limit)
    return [_build_stored_report(row) for row in rows]


@app.get("/api/reports/{domain}", response_model=DomainAnalysisResponse)
async def get_report(domain: str) -> DomainAnalysisResponse:
    domain = domain.lower()
    cached = db.fetch_report_by_domain(domain)
    if cached:
        return _build_domain_analysis(cached)

    analysis = await dns_service.analyze_domain(domain)
    if not analysis.exists:
        raise HTTPException(status_code=404, detail="Domain not found")
    db.save_analysis(analysis, datetime.utcnow().isoformat())
    return analysis
