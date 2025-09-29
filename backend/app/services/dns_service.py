from __future__ import annotations

import asyncio
import contextlib
import json
import pathlib
import re
from typing import Dict, Iterable, List, Pattern, Set

import dns.exception
import dns.resolver

from ..models import DomainAnalysisResponse, ProviderBreakdown, SubdomainInsight

DNS_TIMEOUT = 3.0
RECORD_TYPES = ("A", "AAAA", "MX", "TXT", "NS", "CNAME")
WORDLIST_DEFAULT = pathlib.Path(__file__).resolve().parent.parent / "wordlists" / "common.txt"
PROVIDERS_FILE = pathlib.Path(__file__).resolve().parent.parent / "providers" / "providers.json"


def _load_provider_patterns() -> List[dict]:
    if not PROVIDERS_FILE.exists():
        return []

    with PROVIDERS_FILE.open("r", encoding="utf-8") as handle:
        raw: Dict[str, Dict[str, List[str]]] = json.load(handle)

    compiled: List[dict] = []
    for key, payload in raw.items():
        compiled.append(
            {
                "name": key.replace("_", " ").title(),
                "patterns": {
                    "ns": [re.compile(pattern, re.IGNORECASE) for pattern in payload.get("ns", [])],
                    "mx": [re.compile(pattern, re.IGNORECASE) for pattern in payload.get("mx", [])],
                    "spf": [re.compile(pattern, re.IGNORECASE) for pattern in payload.get("spf", [])],
                    "asn": [re.compile(pattern, re.IGNORECASE) for pattern in payload.get("asn", [])],
                },
            }
        )
    return compiled


PROVIDER_PATTERNS: List[dict] = _load_provider_patterns()


def _new_resolver() -> dns.resolver.Resolver:
    resolver = dns.resolver.Resolver()
    resolver.timeout = DNS_TIMEOUT
    resolver.lifetime = DNS_TIMEOUT
    return resolver


async def _resolve(domain: str, record_type: str) -> List[str]:
    resolver = _new_resolver()
    loop = asyncio.get_running_loop()

    def _query() -> List[str]:
        try:
            answers = resolver.resolve(domain, record_type, raise_on_no_answer=False)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, dns.resolver.NoAnswer):
            return []
        except dns.exception.DNSException:
            return []
        if answers is None:
            return []
        return sorted({str(rdata).rstrip(".") for rdata in answers})

    return await loop.run_in_executor(None, _query)


async def verify_domain(domain: str) -> bool:
    results = await asyncio.gather(
        _resolve(domain, "SOA"),
        _resolve(domain, "A"),
        _resolve(domain, "MX"),
        return_exceptions=True,
    )
    return any(isinstance(item, list) and item for item in results)


async def gather_dns_records(domain: str) -> Dict[str, List[str]]:
    tasks = [(record_type, asyncio.create_task(_resolve(domain, record_type))) for record_type in RECORD_TYPES]
    results: Dict[str, List[str]] = {}

    for record_type, task in tasks:
        try:
            values = await task
        except asyncio.CancelledError:  # pragma: no cover - propagation handled by caller
            raise
        except Exception:
            values = []
        if values:
            results[record_type] = values
    return results


def _classify_provider(mx_hosts: Iterable[str], txt_records: Iterable[str]) -> ProviderBreakdown:
    mx_hosts_lower = [mx.lower() for mx in mx_hosts]
    txt_lower = [txt.lower() for txt in txt_records]

    uses_google = any("google" in host or "aspmx" in host for host in mx_hosts_lower) or any(
        "google-site-verification" in txt for txt in txt_lower
    )
    uses_m365 = any("outlook" in host or "protection.outlook.com" in host for host in mx_hosts_lower) or any(
        "spf.protection.outlook.com" in txt for txt in txt_lower
    )

    if uses_google and uses_m365:
        label = "Google Workspace + Office 365"
    elif uses_google:
        label = "Google Workspace"
    elif uses_m365:
        label = "Office 365"
    else:
        label = "Other / Unknown"

    evidence: Dict[str, List[str]] = {}
    mx_list = list(mx_hosts)
    if mx_list:
        evidence["mx"] = mx_list
    txt_list = list(txt_records)
    if txt_list:
        evidence["txt"] = txt_list

    return ProviderBreakdown(email=label, productivity=label, evidence=evidence)


def _match_patterns(values: Iterable[str], patterns: List[Pattern[str]]) -> bool:
    for value in values:
        for pattern in patterns:
            if pattern.search(value):
                return True
    return False


def _detect_networks(records: Dict[str, List[str]]) -> List[str]:
    if not PROVIDER_PATTERNS:
        return []

    matches: Set[str] = set()
    ns_records = records.get("NS", [])
    mx_records = records.get("MX", [])
    txt_records = records.get("TXT", [])

    other_records: List[str] = []
    for rtype, values in records.items():
        if rtype not in {"NS", "MX", "TXT"}:
            other_records.extend(values)

    for provider in PROVIDER_PATTERNS:
        patterns = provider["patterns"]
        detected = False

        if patterns.get("ns") and _match_patterns(ns_records, patterns["ns"]):
            detected = True
        if not detected and patterns.get("mx") and _match_patterns(mx_records, patterns["mx"]):
            detected = True
        if not detected and patterns.get("spf"):
            detected = _match_patterns(txt_records, patterns["spf"])
        if not detected and patterns.get("asn"):
            detected = _match_patterns(other_records or ns_records or mx_records, patterns["asn"])

        if detected:
            matches.add(provider["name"])

    return sorted(matches)


async def _enumerate_subdomains(domain: str, wordlist_path: pathlib.Path, max_concurrency: int) -> List[SubdomainInsight]:
    if not wordlist_path.exists():
        return []

    with wordlist_path.open("r", encoding="utf-8") as handle:
        candidates = [line.strip() for line in handle if line.strip() and not line.startswith("#")]

    semaphore = asyncio.Semaphore(max_concurrency)
    insights: List[SubdomainInsight] = []

    async def _probe(candidate: str) -> None:
        fqdn = f"{candidate}.{domain}"
        async with semaphore:
            records = await gather_dns_records(fqdn)
        if not records:
            return
        providers = _classify_provider(records.get("MX", []), records.get("TXT", []))
        networks = _detect_networks(records)
        insights.append(SubdomainInsight(fqdn=fqdn, records=records, providers=providers, networks=networks))

    await asyncio.gather(*(_probe(candidate) for candidate in candidates))
    insights.sort(key=lambda item: item.fqdn)
    return insights


async def analyze_domain(
    domain: str,
    *,
    include_subdomains: bool = True,
    wordlist: pathlib.Path | None = None,
    max_concurrency: int = 20,
) -> DomainAnalysisResponse:
    exists = await verify_domain(domain)
    if not exists:
        return DomainAnalysisResponse(
            domain=domain,
            exists=False,
            apex_records={},
            providers=ProviderBreakdown(email="Unknown", productivity="Unknown", evidence={}),
            subdomains=[],
            networks=[],
        )

    apex_records = await gather_dns_records(domain)
    providers = _classify_provider(apex_records.get("MX", []), apex_records.get("TXT", []))
    networks = _detect_networks(apex_records)

    subdomains: List[SubdomainInsight] = []
    if include_subdomains:
        wordlist_path = wordlist or WORDLIST_DEFAULT
        subdomains = await _enumerate_subdomains(domain, wordlist_path, max_concurrency)

    return DomainAnalysisResponse(
        domain=domain,
        exists=True,
        apex_records=apex_records,
        providers=providers,
        subdomains=subdomains,
        networks=networks,
    )
