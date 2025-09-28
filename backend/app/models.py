from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class DomainLookupRequest(BaseModel):
    domain: str = Field(
        ...,
        pattern=r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$",
        description="Domain name to validate",
    )


class DomainLookupResponse(BaseModel):
    domain: str
    exists: bool
    message: str


class ProviderBreakdown(BaseModel):
    email: str
    productivity: str
    evidence: Dict[str, List[str]]


class SubdomainInsight(BaseModel):
    fqdn: str
    records: Dict[str, List[str]]
    providers: ProviderBreakdown


class DomainAnalysisResponse(BaseModel):
    domain: str
    exists: bool
    apex_records: Dict[str, List[str]]
    providers: ProviderBreakdown
    subdomains: List[SubdomainInsight]
