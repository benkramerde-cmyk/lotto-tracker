"""
Lotto 6aus49 Daten Scraper
Holt die letzten 15 Ziehungen von dielottozahlende.net
"""
import json, requests, re, os
from datetime import datetime
from bs4 import BeautifulSoup

OUTPUT = "data/lo.json"

DAYS_DE = {
    "Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch",
    "Thursday":"Donnerstag","Friday":"Freitag","Saturday":"Samstag","Sunday":"Sonntag"
}

def fetch_lo():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LottoBot/1.0)"}
    draws = []

    sources = [
        "https://www.dielottozahlende.net/lotto-6-aus-49",
        "https://lotto.eurojackpot.org/lotto-6aus49",
        "https://www.lotto.net/de/deutsches-lotto/ergebnisse",
    ]

    for url in sources:
        if draws:
            break
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            # Look for result blocks
            tables = soup.find_all("table")
            for table in tables:
                for row in table.find_all("tr")[1:16]:
                    cells = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cells) >= 3:
                        try:
                            date_str = cells[0]
                            nums_raw = " ".join(cells[1:])
                            nums = re.findall(r'\b(\d{1,2})\b', nums_raw)
                            nums = [int(x) for x in nums if 1 <= int(x) <= 49]
                            sz_cands = re.findall(r'\b(\d)\b', nums_raw)
                            sz = int(sz_cands[-1]) if sz_cands else 0

                            if len(nums) >= 6:
                                # Parse date
                                m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
                                if not m:
                                    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
                                    if m:
                                        y,mo,d = m.groups()
                                        date_fmt = f"{d}.{mo}.{y}"
                                    else:
                                        continue
                                else:
                                    d,mo,y = m.groups()
                                    date_fmt = f"{d.zfill(2)}.{mo.zfill(2)}.{y}"

                                d_obj = datetime(int(y), int(mo), int(d))
                                day_de = DAYS_DE.get(d_obj.strftime("%A"), d_obj.strftime("%A"))
                                draws.append({
                                    "date": date_fmt,
                                    "day": day_de,
                                    "nums": nums[:6],
                                    "sz": sz,
                                    "jp": "–"
                                })
                        except Exception as ex:
                            pass

            print(f"  → {url}: {len(draws)} Ziehungen")
        except Exception as e:
            print(f"⚠️  {url}: {e}")

    # Limit to 15
    draws = draws[:15]
    print(f"✅ Lotto: {len(draws)} Ziehungen gefunden")

    # Load existing as fallback
    existing = []
    if os.path.exists(OUTPUT):
        try:
            with open(OUTPUT) as f:
                existing = json.load(f).get("draws", [])
        except:
            pass

    if not draws and existing:
        print("ℹ️  Keine neuen Daten — behalte bestehende")
        draws = existing

    # Sort by date desc
    def sort_key(d):
        try:
            parts = d["date"].split(".")
            return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        except:
            return datetime.min
    draws.sort(key=sort_key, reverse=True)

    output = {
        "updated": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "source": "dielottozahlende.net / lotto.net",
        "draws": draws
    }
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"💾 Gespeichert in {OUTPUT}")

if __name__ == "__main__":
    fetch_lo()
