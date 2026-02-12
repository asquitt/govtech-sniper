"""
RFP Sniper - Route ownership audit tests
========================================
Guards against analytics route ownership drift and duplicate method/path contracts.
"""

import re
from pathlib import Path

from fastapi.routing import APIRoute

from app.main import app


def _analytics_routes() -> list[APIRoute]:
    return [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1/analytics")
    ]


def _frontend_used_analytics_contracts() -> set[tuple[str, str]]:
    repo_root = Path(__file__).resolve().parents[2]
    api_dir = repo_root / "frontend" / "src" / "lib" / "api"
    contracts: set[tuple[str, str]] = set()
    call_pattern = re.compile(r'api\.(get|post|patch|delete)\(\s*"(/analytics/[^"]+)"')
    for file_path in api_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        for method, path in call_pattern.findall(content):
            contracts.add((method.upper(), f"/api/v1{path}"))
    return contracts


def test_analytics_method_path_contracts_are_unique():
    routes = _analytics_routes()
    assert routes, "Expected analytics routes to be registered."

    seen: dict[tuple[str, str], str] = {}
    for route in routes:
        route_methods = set(route.methods or set()) - {"HEAD", "OPTIONS"}
        for method in route_methods:
            key = (method, route.path)
            assert key not in seen, (
                f"Duplicate analytics method/path contract detected for {method} {route.path} "
                f"across {seen[key]} and {route.endpoint.__module__}"
            )
            seen[key] = route.endpoint.__module__


def test_frontend_analytics_paths_have_expected_owners():
    expected = {
        ("GET", "/api/v1/analytics/dashboard"): "app.api.routes.analytics",
        ("GET", "/api/v1/analytics/rfps"): "app.api.routes.analytics",
        ("GET", "/api/v1/analytics/proposals"): "app.api.routes.analytics",
        ("GET", "/api/v1/analytics/ai-usage"): "app.api.routes.analytics",
        ("GET", "/api/v1/analytics/observability"): "app.api.routes.analytics",
        ("GET", "/api/v1/analytics/win-rate"): "app.api.routes.analytics_reporting",
        ("GET", "/api/v1/analytics/pipeline-by-stage"): "app.api.routes.analytics_reporting",
        ("GET", "/api/v1/analytics/conversion-rates"): "app.api.routes.analytics_reporting",
        ("GET", "/api/v1/analytics/proposal-turnaround"): "app.api.routes.analytics_reporting",
        ("GET", "/api/v1/analytics/naics-performance"): "app.api.routes.analytics_reporting",
        ("POST", "/api/v1/analytics/export"): "app.api.routes.analytics_reporting",
    }

    ownership: dict[tuple[str, str], str] = {}
    for route in _analytics_routes():
        route_methods = set(route.methods or set()) - {"HEAD", "OPTIONS"}
        for method in route_methods:
            ownership[(method, route.path)] = route.endpoint.__module__

    for key, module_prefix in expected.items():
        assert key in ownership, f"Missing analytics contract for {key[0]} {key[1]}"
        assert ownership[key].startswith(module_prefix), (
            f"Route {key[0]} {key[1]} owned by {ownership[key]} "
            f"instead of expected module prefix {module_prefix}"
        )


def test_frontend_unused_analytics_endpoints_are_flagged_for_retirement_candidates():
    route_contracts: set[tuple[str, str]] = set()
    for route in _analytics_routes():
        route_methods = set(route.methods or set()) - {"HEAD", "OPTIONS"}
        for method in route_methods:
            route_contracts.add((method, route.path))

    frontend_used_contracts = _frontend_used_analytics_contracts()
    frontend_unused = {
        contract for contract in route_contracts if contract not in frontend_used_contracts
    }
    expected_retirement_candidates = {
        ("GET", "/api/v1/analytics/documents"),
        ("GET", "/api/v1/analytics/slo"),
        ("GET", "/api/v1/analytics/alerts"),
    }

    assert frontend_unused == expected_retirement_candidates, (
        "Frontend-unused analytics contracts changed. Review retirement candidates: "
        f"{sorted(frontend_unused)}"
    )
