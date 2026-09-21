from __future__ import annotations
import hashlib, html, json, os, re, time
from pathlib import Path
from typing import Any
import feedparser, requests
from config import FEEDS, FREE_KEYWORDS, MAX_POSTS_PER_RUN, MAX_PRICE, MIN_DISCOUNT, REQUEST_TIMEOUT, SKIP_KEYWORDS, VK_API, VK_API_VERSION

SEEN_PATH = Path(__file__).parent / "data" / "seen.json"
USER_AGENT = "VK-Game-Deals-Bot/1.0"

def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def first_number(value: str) -> float | None:
    m = re.search(r"(?<!\d)(\d+(?:[.,]\d+)?)", value or "")
    return float(m.group(1).replace(",", ".")) if m else None

def detect_discount(text: str) -> int | None:
    for pattern in (r"(?:-|−)\s*(\d{1,3})\s*%", r"(\d{1,3})\s*%\s*(?:off|скид)", r"(?:скидка|discount)\D{0,15}(\d{1,3})\s*%"):
        m = re.search(pattern, text, re.I)
        if m: return int(m.group(1))
    return None

def is_free(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in FREE_KEYWORDS)

def should_skip(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    return any(k in text for k in SKIP_KEYWORDS)

def load_seen() -> dict[str, float]:
    if not SEEN_PATH.exists(): return {}
    try: return json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return {}

def save_seen(seen: dict[str, float]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    trimmed = dict(sorted(seen.items(), key=lambda x: x[1], reverse=True)[:2000])
    SEEN_PATH.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")

def item_key(item: dict[str, Any]) -> str:
    raw = "|".join((item.get("source",""), item.get("title",""), item.get("link","")))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def parse_feed(source: dict[str, str]) -> list[dict[str, Any]]:
    try:
        response = requests.get(source["url"], timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
    except requests.RequestException as exc:
        print(f"[WARN] {source['name']}: {exc}")
        return []
    items = []
    for entry in parsed.entries[:50]:
        title = clean_text(entry.get("title",""))
        description = clean_text(entry.get("summary","") or entry.get("description",""))
        link = entry.get("link","").strip()
        if not title or not link or should_skip(title, description): continue
        full = f"{title} {description}"
        discount, free, price = detect_discount(full), is_free(full), first_number(description)
        if not (free or (discount is not None and discount >= MIN_DISCOUNT)): continue
        if not free and price is not None and price > MAX_PRICE and discount is not None and discount < max(MIN_DISCOUNT+15,70): continue
        items.append({"source":source["name"],"title":title,"description":description,"link":link,"discount":discount,"free":free,"price":price})
    return items

def score(item: dict[str, Any]) -> tuple[int,int]:
    return (1000,0) if item["free"] else (item["discount"] or 0, 1 if item["price"] is not None else 0)

def format_post(item: dict[str, Any]) -> str:
    headline = "🎁 БЕСПЛАТНО" if item["free"] else f"🔥 СКИДКА {item['discount']}%"
    return f"{headline}\n\n🎮 {item['title']}\n\n🏪 {item['source']}\n🔗 {item['link']}\n\n#игры #скидки #game_deals"

def vk_post(message: str) -> None:
    token, group_id = os.getenv("VK_TOKEN"), os.getenv("VK_GROUP_ID")
    if not token or not group_id: raise RuntimeError("VK_TOKEN/VK_GROUP_ID are not configured")
    response = requests.post(f"{VK_API}/wall.post", data={"access_token":token,"v":VK_API_VERSION,"owner_id":-int(group_id),"from_group":1,"message":message}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload: raise RuntimeError(payload["error"].get("error_msg","VK API error"))
    print(f"[OK] VK post id={payload.get('response',{}).get('post_id')}")

def main() -> None:
    seen = load_seen()
    candidates = []
    for source in FEEDS: candidates.extend(parse_feed(source))
    candidates = sorted({item_key(x):x for x in candidates}.values(), key=score, reverse=True)
    published, now = 0, time.time()
    for item in candidates:
        key = item_key(item)
        if key in seen: continue
        post = format_post(item)
        print("\n---\n"+post)
        if os.getenv("DRY_RUN","0") == "1":
            seen[key] = now
            continue
        try:
            vk_post(post); seen[key] = now; published += 1
            if published >= MAX_POSTS_PER_RUN: break
            time.sleep(2)
        except Exception as exc: print(f"[ERROR] Failed to publish '{item['title']}': {exc}")
    save_seen(seen)
    print(f"[DONE] candidates={len(candidates)}, published={published}")

if __name__ == "__main__": main()
