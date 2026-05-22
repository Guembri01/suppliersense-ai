"""Capture a fresh set of product screenshots — runs against a live dev server.

Usage (with backend on :8030 and frontend on :5030):
    python backend/scripts/capture_screenshots.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "project-audit" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

APP = "http://localhost:5030"
VIEWPORT = {"width": 1440, "height": 900}

EMAIL = "admin@suppliersense.test"
PASSWORD = "Admin123!"


def log(msg: str) -> None:
    print(f"  • {msg}", flush=True)


def shot(page, name: str, full_page: bool = True) -> None:
    path = OUT / name
    page.screenshot(path=str(path), full_page=full_page)
    log(f"saved {name} ({path.stat().st_size // 1024} KB)")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = ctx.new_page()

        # ── 1. Login screen ──
        log("opening login")
        page.goto(APP, wait_until="networkidle")
        page.wait_for_selector("input[type=email]", timeout=10_000)
        time.sleep(0.4)  # let the gradient/blur settle
        shot(page, "01_login.png", full_page=False)

        # ── Authenticate ──
        page.fill("input[type=email]", EMAIL)
        page.fill("input[type=password]", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_url(f"{APP}/", timeout=15_000)
        page.wait_for_selector("text=Dashboard", timeout=10_000)

        # Dashboard waits for /ai/briefing — let it land before capture
        page.wait_for_function(
            "() => document.body.innerText.includes('AI Executive Briefing') "
            "&& !document.body.innerText.includes('Loading…')",
            timeout=15_000,
        )
        time.sleep(0.8)  # count-up animation
        shot(page, "02_dashboard.png")

        # ── 3. Suppliers list ──
        page.click("a[href='/suppliers']")
        page.wait_for_selector("table tbody tr", timeout=10_000)
        # ensure rows have populated (not the "Loading..." row)
        page.wait_for_function(
            "() => document.querySelectorAll('table tbody tr').length >= 3",
            timeout=10_000,
        )
        time.sleep(0.4)
        shot(page, "03_suppliers.png")

        # ── 4. Supplier Detail (first row — highest-risk after sort) ──
        page.locator("table tbody tr").first.click()
        page.wait_for_selector("text=Overview", timeout=10_000)
        # Click AI Reanalysis so the narrative panel renders
        try:
            page.get_by_role("button", name="AI Reanalysis").click(timeout=5_000)
            page.wait_for_selector("text=AI Risk Analysis", timeout=15_000)
            time.sleep(0.6)
        except PWTimeoutError:
            log("AI Reanalysis button not found — continuing anyway")
        shot(page, "04_supplier_detail_ai_narrative.png")

        # ── 4b. Risk Profile sub-tab ──
        try:
            page.locator("button", has_text="Risk Profile").first.click(timeout=5_000)
            time.sleep(0.3)
            shot(page, "05_supplier_risk_profile.png")
        except PWTimeoutError:
            pass

        # ── 4c. Voice Audit sub-tab ──
        try:
            page.locator("button", has_text="Voice Audit").first.click(timeout=5_000)
            time.sleep(0.3)
            page.locator("button", has_text="Cross-Validate Voice").first.click(timeout=5_000)
            page.wait_for_selector("text=Voice", timeout=15_000)
            time.sleep(0.6)
            shot(page, "06_supplier_voice_audit.png")
        except PWTimeoutError:
            log("Voice Audit panel not captured")

        # ── 5. Geopolitical (the previously-broken route) ──
        page.goto(f"{APP}/geopolitical", wait_until="networkidle")
        page.wait_for_selector("text=Geopolitical Risk Monitor", timeout=10_000)
        time.sleep(0.3)
        shot(page, "07_geopolitical.png")

        # ── 6. Disruptions ──
        page.goto(f"{APP}/disruptions", wait_until="networkidle")
        page.wait_for_selector("text=Disruptions", timeout=10_000)
        time.sleep(0.3)
        shot(page, "08_disruptions.png")

        # ── 7. Alerts ──
        page.goto(f"{APP}/alerts", wait_until="networkidle")
        page.wait_for_selector("text=Risk Alerts", timeout=10_000)
        time.sleep(0.3)
        shot(page, "09_alerts.png")

        # ── 8. Analytics ──
        page.goto(f"{APP}/analytics", wait_until="networkidle")
        page.wait_for_selector("text=Suppliers by Risk Band", timeout=10_000)
        time.sleep(0.4)
        shot(page, "10_analytics.png")

        # ── 9. AI Ask widget — open + ask + capture ──
        page.goto(f"{APP}/", wait_until="networkidle")
        page.wait_for_function(
            "() => document.body.innerText.includes('AI Executive Briefing')",
            timeout=10_000,
        )
        page.get_by_role("button", name="Ask AI assistant").click(timeout=5_000)
        page.wait_for_selector("text=Portfolio assistant", timeout=5_000)
        # Click a suggested starter
        page.locator("text=Which suppliers are highest risk right now?").click()
        page.wait_for_selector("text=Top 5 highest-risk suppliers", timeout=15_000)
        time.sleep(0.4)
        shot(page, "11_ai_ask_widget.png", full_page=False)

        browser.close()
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
