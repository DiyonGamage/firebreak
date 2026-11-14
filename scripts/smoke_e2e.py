from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("PMMA", "iss_internal", "A", "high_risk"),
    ("PMMA", "lunar_surface", "C", "test_needed"),
    ("Silicone", "iss_internal", "B", "test_needed"),
    ("SIBAL", "iss_internal", "A", "high_risk"),
    ("Nomex", "iss_internal", "B", "test_needed"),
    ("Kevlar/PBI", "lunar_surface", "C", "test_needed"),
    ("unobtainium", "iss_internal", "D", "insufficient_evidence"),
]

ASSISTANT_CASES = [
    ("Assess PMMA at ISS internal", "assess_material"),
    ("Find evidence gaps for Gateway", "find_gaps"),
    ("Check coverage for SIBAL at airlock", "coverage_check"),
    ("PMMA severity", "severity_estimate"),
    ("Find evidence for Nomex", "retrieve_evidence"),
]


def get_json(base: str, path: str, timeout: int = 60) -> dict:
    with urllib.request.urlopen(base + path, timeout=timeout) as response:
        return json.load(response)


def check_api(base: str) -> list[str]:
    failures = []
    stats = get_json(base, "/api/stats")
    expectations = {
        "total": 637,
        "solid": 148,
        "documents": 9,
        "pages": 501,
        "atmospheres": 8,
    }
    for key, expected in expectations.items():
        if stats.get(key) != expected:
            failures.append(f"stats.{key}={stats.get(key)!r}, expected {expected!r}")
    auc = (stats.get("ml_metrics") or {}).get("auc")
    if auc != 0.811:
        failures.append(f"stats.ml_metrics.auc={auc!r}, expected 0.811")

    for material, atmosphere, grade, verdict in CASES:
        query = urllib.parse.urlencode({"material": material, "atmosphere": atmosphere})
        result = get_json(base, f"/api/assess?{query}")
        if result.get("grade") != grade or result.get("verdict") != verdict:
            failures.append(
                f"{material}/{atmosphere}: grade={result.get('grade')}, "
                f"verdict={result.get('verdict')}; expected {grade}/{verdict}"
            )
        if grade != "D" and not result.get("evidence"):
            failures.append(f"{material}/{atmosphere}: no evidence rows returned")
        print(
            f"API assess {material:12s} {atmosphere:14s} -> "
            f"{result.get('grade')} / {result.get('verdict')} "
            f"({len(result.get('evidence', []))} rows)"
        )

    gaps = get_json(base, "/api/gap-map?atmosphere=iss_internal")
    gap_rows = gaps if isinstance(gaps, list) else gaps.get("gaps", [])
    classes = {row["material_class"]: row["grade"] for row in gap_rows}
    for material_class, grade in {
        "PMMA": "A",
        "SIBAL": "A",
        "Nomex": "B",
        "Silicone": "B",
        "Kevlar/PBI": "C",
    }.items():
        if classes.get(material_class) != grade:
            failures.append(f"gap map {material_class}={classes.get(material_class)!r}, expected {grade!r}")
    print(f"API gap map -> {len(gap_rows)} rows, Kevlar/PBI={classes.get('Kevlar/PBI')}")

    docs = get_json(base, "/api/documents?q=PMMA%20margin")
    doc_rows = docs if isinstance(docs, list) else docs.get("results", [])
    if not doc_rows:
        failures.append("document search returned no results for 'PMMA margin'")
    print(f"API documents -> {len(doc_rows)} hits for 'PMMA margin'")

    for query, expected_tool in ASSISTANT_CASES:
        result = get_json(base, "/api/assistant?" + urllib.parse.urlencode({"q": query}))
        if result.get("tool") != expected_tool:
            failures.append(f"assistant {query!r}: tool={result.get('tool')!r}, expected {expected_tool!r}")
        print(f"API assistant {query!r} -> {result.get('tool')}")

    clarification = get_json(
        base, "/api/assistant?" + urllib.parse.urlencode({"q": "What is safe?"})
    )
    if not clarification.get("needs_clarification"):
        failures.append("assistant did not ask for a material on an under-specified query")
    print(f"API assistant under-specified -> clarification={clarification.get('needs_clarification')}")
    return failures


def check_ui(base: str) -> list[str]:
    failures = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        external_requests: list[str] = []

        def track(request) -> None:
            if not request.url.startswith(base) and not request.url.startswith("data:"):
                external_requests.append(request.url)

        page.on("request", track)
        page.goto(base + "/", wait_until="networkidle")

        page.fill("#material", "PMMA")
        page.select_option("#atmosphere", "iss_internal")
        page.click("button.primary")
        page.wait_for_selector(".grade-letter")
        grade = page.locator(".grade-letter").inner_text().strip()
        if grade != "A":
            failures.append(f"UI form grade={grade!r}, expected 'A'")
        if page.locator(".ledger table tbody tr").count() < 5:
            failures.append("UI evidence ledger has fewer than 5 rows")
        print(
            f"UI form submit -> grade {grade}, "
            f"{page.locator('.ledger table tbody tr').count()} ledger rows"
        )

        page.fill("#assistant-query", "Assess SIBAL at ISS internal")
        page.click("#assistant-form button[type=submit]")
        page.wait_for_function(
            "() => { const el = document.querySelector('#assistant-answer');"
            " return el && !el.hidden && el.textContent.length > 20"
            " && !el.textContent.includes('Routing'); }",
            timeout=30000,
        )
        answer = page.locator("#assistant-answer").inner_text()
        trace = page.locator("#assistant-trace").inner_text()
        if "grade" not in answer.lower():
            failures.append(f"UI assistant answer looked wrong: {answer[:120]!r}")
        if "fallback" not in trace:
            failures.append(f"UI assistant trace missing fallback engine: {trace[:120]!r}")
        print(f"UI assistant -> {answer[:100]}...")
        print(f"UI assistant trace -> {trace.splitlines()[0]}")

        page.goto(base + "/library?q=PMMA%20margin", wait_until="networkidle")
        hits = page.locator(".hit").count()
        if hits < 1:
            failures.append("UI library search returned no hits")
        print(f"UI library search -> {hits} hits")
        if external_requests:
            failures.append(f"UI made external requests: {external_requests[:3]}")
        print(f"UI external requests -> {len(external_requests)}")
        browser.close()
    return failures


def check_cactus(base: str) -> list[str]:
    failures = []
    query = urllib.parse.urlencode(
        {"q": "Assess SIBAL at ISS internal", "engine": "cactus"}
    )
    try:
        result = get_json(base, f"/api/assistant?{query}", timeout=180)
    except Exception as exc:
        return [f"Cactus request failed: {exc}"]
    print(f"Cactus -> engine={result.get('engine')!r}, tool={result.get('tool')!r}")
    if result.get("engine_error"):
        failures.append(f"Cactus engine error: {result['engine_error']}")
    trace = result.get("trace") or []
    if result.get("engine") == "cactus-needle":
        names = [item.get("name") for item in trace]
        print(f"Cactus trace -> {names}")
        if "assess_material" not in names:
            failures.append(f"Cactus routed to {names}, expected assess_material")
    else:
        failures.append(
            f"Cactus returned engine={result.get('engine')!r} instead of cactus-needle"
        )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--cactus", action="store_true")
    args = parser.parse_args()
    failures = check_api(args.base_url)
    failures += check_ui(args.base_url)
    if args.cactus:
        failures += check_cactus(args.base_url)
    print("\n" + ("PASS" if not failures else "FAIL"))
    for failure in failures:
        print(f"- {failure}")
    raise SystemExit(0 if not failures else 1)


if __name__ == "__main__":
    main()
