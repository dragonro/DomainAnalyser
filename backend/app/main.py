from __future__ import annotations

import pathlib

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from .models import DomainAnalysisResponse, DomainLookupRequest, DomainLookupResponse
from .services import dns_service

app = FastAPI(title="Domain Analyzer API", version="0.1.0")

FRONTEND_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


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
    return analysis


@app.get("/api/reports/{domain}", response_model=DomainAnalysisResponse)
async def get_report(domain: str) -> DomainAnalysisResponse:
    domain = domain.lower()
    analysis = await dns_service.analyze_domain(domain)
    if not analysis.exists:
        raise HTTPException(status_code=404, detail="Domain not found")
    return analysis
