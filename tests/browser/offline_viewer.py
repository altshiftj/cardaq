import re
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import Page, expect, sync_playwright


class OfflineViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        directory = Path(cls.enterClassContext(TemporaryDirectory()))
        header = "elapsed_s,event,request,reply,ecm_vehicle_speed_kph,ecm_engine_speed_rpm\n"
        cold = directory / "cold.csv"
        cold.write_text(
            header
            + "0,reply,,,0,0\n1,reply,,,0,0\n2,reply,,,0,900\n3,reply,,,15,1000\n"
            + "".join(
                f"{time},reply,06A3,18DAF110 10 0A 46 A3 0C 24 00 {count:02X} | "
                "18DAF110 21 00 00 FF FF,,\n"
                for time, count in ((0.5, 3), (2.5, 5), (3.5, 5), (4.5, 0), (5.5, 1))
            ),
            encoding="utf-8",
        )
        steady = directory / "steady.csv"
        steady.write_text(header + "0,reply,,,36,1400\n1,reply,,,36,1400\n", encoding="utf-8")
        output = directory / "comparison.html"
        subprocess.run(
            [
                sys.executable, "-m", "cardaq", "view", str(cold), str(steady),
                "--label", "Cold start", "--label", "Steady drive", "--output", str(output),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            timeout=30,
        )
        cls.url = output.as_uri()
        playwright = cls.enterClassContext(sync_playwright())
        cls.browser = playwright.chromium.launch()
        cls.addClassCleanup(cls.browser.close)

    def open_report(self, width: int) -> Page:
        context = self.browser.new_context(offline=True, locale="en-US", viewport={"width": width, "height": 900})
        self.addCleanup(context.close)
        page = context.new_page()
        page.goto(self.url)
        return page

    def test_event_focus_follows_the_selected_recordings(self) -> None:
        page = self.open_report(1280)
        cold = page.get_by_role("checkbox", name="Cold start")
        steady = page.get_by_role("checkbox", name="Steady drive")
        stats = page.get_by_role("group", name="Selected signal statistics")
        window = page.get_by_role("combobox", name="Time window")
        event = page.get_by_text("Cold start · Engine start · 0m 02s", exact=True)

        expect(cold).to_be_checked()
        expect(steady).to_be_checked()
        expect(stats.get_by_text("Cold start", exact=True)).to_be_visible()
        expect(stats.get_by_text("Steady drive", exact=True)).to_be_visible()

        page.get_by_role("button", name=re.compile("Engine start")).click()
        expect(event).to_be_visible()
        expect(window).to_have_value("event")
        steady.uncheck()
        expect(event).to_be_visible()
        steady.check()

        cold.uncheck()
        expect(event).to_be_hidden()
        expect(window).to_have_value("full")
        expect(stats.get_by_text("Cold start", exact=True)).to_have_count(0)
        expect(stats).to_contain_text("1,400 rpm")

        steady.uncheck()
        expect(page.get_by_text("Select a recording to see its charts.")).to_be_visible()
        expect(stats).to_be_hidden()
        page.get_by_role("button", name="Show all recordings").click()
        expect(cold).to_be_checked()
        expect(steady).to_be_checked()
        expect(stats.get_by_text("Cold start", exact=True)).to_be_visible()
        expect(stats.get_by_text("Steady drive", exact=True)).to_be_visible()
        expect(window).to_have_value("full")

    def test_misfire_intervals_and_totals_belong_to_the_selected_drive(self) -> None:
        page = self.open_report(390)
        panel = page.locator("#misfire-history")
        first_interval = "Cylinder 2 · 0:00.5 to 0:02.5 elapsed · counter 3 → 5 (+2)"
        second_interval = "Cylinder 2 · 0:04.5 to 0:05.5 elapsed · counter 0 → 1 (+1)"
        first = panel.get_by_role("button", name=first_interval, exact=True)
        second = panel.get_by_role("button", name=second_interval, exact=True)
        total = panel.get_by_role("img", name=re.compile(r"^Cumulative observed misfires\..*Cylinder 2, 3\."))

        panel.get_by_text("When counts rose", exact=True).press("Tab")
        expect(first).to_be_focused()
        expect(panel.locator('[aria-live="polite"]')).to_have_text(first_interval)
        page.keyboard.press("Tab")
        expect(second).to_be_focused()
        expect(panel.locator('[aria-live="polite"]')).to_have_text(second_interval)
        expect(total).to_be_visible()
        expect(panel.get_by_text("Detection intervals (2)", exact=True)).to_be_visible()

        drive = panel.get_by_role("combobox", name="Drive")
        drive.select_option(label="Steady drive")
        expect(panel.get_by_text("This drive has no valid cylinder misfire readings.")).to_be_visible()
        expect(total).to_be_hidden()
        expect(first).to_be_hidden()
        drive.select_option(label="Cold start")
        expect(total).to_be_visible()
