import re
import requests
from playwright.sync_api import sync_playwright

URL = "https://nhmpe.seetickets.com/timeslot/nhmpe"

# ここはあなたの ntfy トピック名
NTFY_TOPIC = "nhmpe-7392kx81"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

DAY_RE = re.compile(r"^(?:[1-9]|[12]\d|3[01])$")

def push(title: str, message: str):
    requests.post(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={"Title": title},
        timeout=10,
    )

def parse_rgb(s: str):
    s = (s or "").strip().lower()
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", s)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def is_orange(bg_css: str) -> bool:
    rgb = parse_rgb(bg_css)
    if not rgb:
        return False
    r, g, b = rgb
    # “塗りつぶしオレンジっぽい”判定（必要なら後で微調整）
    return r >= 200 and g >= 120 and b <= 120

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)

        elements = page.locator("button, a, div, span")
        count = elements.count()

        open_days = []
        for i in range(count):
            el = elements.nth(i)
            try:
                txt = (el.inner_text() or "").strip()
                if not DAY_RE.match(txt):
                    continue

                box = el.bounding_box()
                if not box or box["width"] < 25 or box["height"] < 20:
                    continue

                info = el.evaluate(
                    """(node) => {
                        const s = window.getComputedStyle(node);
                        return { cursor: s.cursor, bg: s.backgroundColor };
                    }"""
                )

                # 空きなしはカーソル not-allowed（あなたの説明どおり）
                if (info.get("cursor") or "").lower() == "not-allowed":
                    continue

                if is_orange(info.get("bg") or ""):
                    open_days.append(int(txt))
            except Exception:
                continue

        browser.close()

    if open_days:
        open_days = sorted(set(open_days))
        msg = "カレンダーで“塗りつぶしオレンジ”の日付を検知:\n" + "\n".join(f"- {d}日" for d in open_days) + f"\n\n{URL}"
        push("NHMPE: 空き検知", msg)

if __name__ == "__main__":
    push("テスト", "GitHub Actionsからのテスト通知")
    main()
