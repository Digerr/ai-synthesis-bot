import os

FEEDS = [
    {"name": "Steam", "url": "https://steam-deals.henrylok.me/feed.xml"},
    {"name": "Epic Games", "url": "https://rsshub.app/epicgames/freegames/en_US/us"},
]
MIN_DISCOUNT = int(os.getenv("MIN_DISCOUNT", "50"))
MAX_PRICE = float(os.getenv("MAX_PRICE", "15"))
MAX_POSTS_PER_RUN = int(os.getenv("MAX_POSTS_PER_RUN", "3"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
FREE_KEYWORDS = ("free giveaway", "free to keep", "free game", "бесплатно", "раздача")
SKIP_KEYWORDS = ("demo", "prologue", "playtest", "soundtrack", "dlc")
VK_API = "https://api.vk.com/method"
VK_API_VERSION = "5.199"
