import time
import re
import requests
from playwright.sync_api import sync_playwright

URL = "https://nhmpe.seetickets.com/timeslot/nhmpe"

NTFY_TOPIC = "nhmpe-7392kx81"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

INTERVAL = 120

DAY_RE = re.compile(r"^(?:[1-9]|[12]\d|3[01])$")

def push(title, message):
    requests.post(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={"Title": title},
        timeout=10,
    )

def parse_rgb(s):
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", (s or ""))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def is_orange(bg):
    parsed = parse_rgb(bg)
    if not parsed:
        return False
    r, g, b = parsed
    return r >= 200 and g >= 120 and b <= 120

def main():
    last = None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        while True:
            try:
                page.goto(URL)
                page.wait_for_timeout(1500)

                elements = page.locator("button, a, div, span")
                count = elements.count()
                found = []

                for i in range(count):
                    el = elements.nth(i)
                    txt = (el.inner_text() or "").strip()
                    if not DAY_RE.match(txt):
                        continue

                    info = el.evaluate("""
                        (node) => {
                            const s = window.getComputedStyle(node);
                            return {
                                cursor: s.cursor,
                                bg: s.backgroundColor
                            }
                        }
                    """)

                    if info["cursor"] != "not-allowed" and is_orange(info["bg"]):
                        found.append(txt)

                if found:
                    fingerprint = ",".join(found)
                    if fingerprint != last:
                        push(
                            "NHMPE: 空き検知",
                            "空きが出た可能性:\n" + "\n".join(found) + "\n" + URL
                        )
                        last = fingerprint
                else:
                    last = None

            except Exception:
                pass

            time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
