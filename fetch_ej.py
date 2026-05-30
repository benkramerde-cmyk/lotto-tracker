"""
Eurojackpot Daten Scraper
Holt die letzten 15 Ziehungen von euro-jackpot.net
"""
import json, requests, re, os
from datetime import datetime
from bs4 import BeautifulSoup

OUTPUT = "data/ej.json"
URL    = "https://www.euro-jackpot.net/de/gewinnzahlen-archiv-2026"

DAYS_DE = {
    "Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch",
    "Thursday":"Donnerstag","Friday":"Freitag","Saturday":"Samstag","Sunday":"Sonntag"
}
MONTHS_EN2DE = {
    "January":"Januar","February":"Februar","March":"März","April":"April",
    "May":"Mai","June":"Juni","July":"Juli","August":"August",
    "September":"September","October":"Oktober","November":"November","December":"Dezember"
}

def parse_date_de(raw: str):
    """'Freitag, 22. Mai 2026' → ('22.05.2026', 'Freitag')"""
    parts = raw.strip().rstrip(".").split(",")
    day_name = parts[0].strip()
    date_part = parts[1].strip() if len(parts) > 1 else parts[0].strip()
    # date_part like "22. Mai 2026"
    m = re.search(r'(\d+)\.\s+(\w+)\s+(\d{4})', date_part)
    if not m:
        return None, None
    d, month_de, y = m.group(1), m.group(2), m.group(3)
    month_map = {
        "Januar":"01","Februar":"02","März":"03","April":"04","Mai":"05","Juni":"06",
        "Juli":"07","August":"08","September":"09","Oktober":"10","November":"11","Dezember":"12"
    }
    mo = month_map.get(month_de, "00")
    return f"{d.zfill(2)}.{mo}.{y}", day_name

def fetch_ej():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LottoBot/1.0)"}
    draws = []

    try:
        r = requests.get(URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # Look for draw result rows
        rows = soup.select("table tr, .result-row, .draw-result")
        if not rows:
            # Try generic approach: find all text with number patterns
            text = r.text

        # Parse from JSON-like structure in page
        # euro-jackpot.net embeds data as structured HTML
        results = soup.find_all("li", class_=re.compile("result|draw|winning", re.I))

        # Fallback: scrape the archive table
        tables = soup.find_all("table")
        for table in tables:
            for row in table.find_all("tr")[1:]:  # skip header
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) >= 2:
                    date_str = cells[0]
                    nums_str = cells[1] if len(cells) > 1 else ""
                    # Try to parse numbers like "5 34 35 42 46 3 5"
                    nums = re.findall(r'\d+', nums_str)
                    if len(nums) == 7:
                        date, day = parse_date_de(date_str)
                        if date:
                            draws.append({
                                "date": date, "day": day,
                                "main": [int(x) for x in nums[:5]],
                                "euro": [int(x) for x in nums[5:7]],
                                "jackpot": False, "jp": "–"
                            })

    except Exception as e:
        print(f"⚠️  Scraping error: {e}")

    # If we got nothing, try alternative URL
    if not draws:
        try:
            alt_url = "https://winnersystem.org/en/eurojackpot/archiv/"
            r = requests.get(alt_url, headers=headers, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            tables = soup.find_all("table")
            for table in tables:
                for row in table.find_all("tr")[1:17]:
                    cells = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cells) >= 7:
                        try:
                            raw_date = cells[0]  # e.g. "22.05.2026"
                            main = [int(cells[i]) for i in range(1,6)]
                            euro = [int(cells[i]) for i in range(6,8)]
                            # parse date
                            parts = raw_date.split(".")
                            if len(parts) == 3:
                                d_obj = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                                day_de = DAYS_DE.get(d_obj.strftime("%A"), d_obj.strftime("%A"))
                                draws.append({
                                    "date": raw_date,
                                    "day": day_de,
                                    "main": main,
                                    "euro": euro,
                                    "jackpot": False,
                                    "jp": "–"
                                })
                        except:
                            pass
        except Exception as e:
            print(f"⚠️  Alt source error: {e}")

    # Limit to latest 15
    draws = draws[:15]
    print(f"✅ EJ: {len(draws)} Ziehungen gefunden")

    # Load existing data to merge
    existing = []
    if os.path.exists(OUTPUT):
        try:
            with open(OUTPUT) as f:
                existing = json.load(f).get("draws", [])
        except:
            pass

    # Merge: keep existing if no new data found
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
        "source": "euro-jackpot.net / winnersystem.org",
        "draws": draws
    }
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"💾 Gespeichert in {OUTPUT}")

if __name__ == "__main__":
    fetch_ej()
