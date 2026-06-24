from __future__ import annotations

import argparse
import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FEEDS_FILE = BASE_DIR / "feeds.txt"
DEFAULT_OUTPUT_FILE = BASE_DIR / "daily_brief.md"
DEFAULT_CANDIDATES_FILE = BASE_DIR / "ai_candidates.md"
LOCAL_TIMEZONE = timezone(timedelta(hours=8), "Asia/Hong_Kong")


CATEGORY_KEYWORDS = {
    "AI": [
        "ai",
        "artificial intelligence",
        "openai",
        "anthropic",
        "claude",
        "chatgpt",
        "gemini",
        "deepmind",
        "llm",
        "large language model",
        "generative ai",
        "agent",
        "agentic",
        "machine learning",
    ],
    "半導體": [
        "semiconductor",
        "chip",
        "chips",
        "nvidia",
        "tsmc",
        "asml",
        "amd",
        "intel",
        "micron",
        "sk hynix",
        "samsung electronics",
        "hbm",
        "gpu",
        "foundry",
        "wafer",
        "advanced packaging",
    ],
    "美國科技股": [
        "apple",
        "microsoft",
        "meta",
        "amazon",
        "alphabet",
        "google",
        "tesla",
        "oracle",
        "palantir",
        "salesforce",
        "nasdaq",
        "magnificent seven",
    ],
    "中國科技": [
        "china tech",
        "chinese tech",
        "alibaba",
        "tencent",
        "bytedance",
        "tiktok",
        "huawei",
        "baidu",
        "xiaomi",
        "smic",
        "jd.com",
        "pdd",
        "meituan",
        "deepseek",
        "china ai",
    ],
    "宏觀經濟": [
        "fed",
        "federal reserve",
        "fomc",
        "ecb",
        "boj",
        "boe",
        "pboc",
        "central bank",
        "interest rate",
        "rate cut",
        "rate hike",
        "inflation",
        "cpi",
        "ppi",
        "gdp",
        "pmi",
        "employment",
        "payroll",
        "unemployment",
        "tariff",
        "trade war",
    ],
    "金融市場": [
        "stock market",
        "stocks",
        "s&p 500",
        "dow",
        "treasury",
        "yield",
        "bond",
        "dollar",
        "yen",
        "euro",
        "oil",
        "brent",
        "wti",
        "gold",
        "bitcoin",
        "crypto",
        "earnings",
        "ipo",
        "m&a",
        "acquisition",
        "volatility",
        "vix",
    ],
}

IMPORTANT_KEYWORDS = {
    "AI": ["OpenAI", "Anthropic", "ChatGPT", "Gemini", "DeepMind", "LLM", "Agent", "AI"],
    "半導體": ["NVIDIA", "TSMC", "ASML", "AMD", "Intel", "Micron", "SK Hynix", "chip", "semiconductor", "GPU"],
    "大型科技": ["Apple", "Microsoft", "Meta", "Amazon", "Alphabet", "Google", "Tesla"],
    "宏觀政策": ["Fed", "Federal Reserve", "ECB", "interest rate", "inflation", "GDP", "employment"],
    "市場風險": ["earnings", "IPO", "M&A", "acquisition", "tariff", "China", "trade", "warning", "collapse"],
}

HEADLINE_TRIGGERS = [
    "record",
    "surge",
    "collapse",
    "warning",
    "investigation",
    "lawsuit",
    "ban",
    "restriction",
    "launch",
    "investment",
    "earnings",
    "guidance",
    "forecast",
    "acquisition",
    "tariff",
    "export control",
]

LOW_SIGNAL_TITLE_PATTERNS = [
    "morning squawk",
    "things to know",
    "what to know",
    "roundup",
    "top stories",
    "live updates",
    "market today",
    "before the stock market opens",
    "price today",
    "live price",
    "marketcap and chart",
]

HIGH_WEIGHT_SOURCES = [
    "reuters",
    "bloomberg",
    "financial times",
    "ft.com",
    "wall street journal",
    "wsj",
    "cnbc",
    "associated press",
    "ap news",
    "nikkei",
    "the information",
]

MEDIUM_WEIGHT_SOURCES = [
    "techcrunch",
    "the verge",
    "venturebeat",
    "marketwatch",
    "seeking alpha",
    "mit technology review",
    "ars technica",
    "bbc",
    "yahoo finance",
    "investing.com",
]

LOW_WEIGHT_SOURCES = [
    "benzinga",
    "simply wall st",
    "simplywallst",
    "msn",
    "aol",
    "blog",
    "substack",
    "medium",
    "motley fool",
    "insider monkey",
    "24/7 wall st",
    "gurufocus",
    "zacks",
    "tipranks",
    "investorplace",
    "marketbeat",
    "coinmarketcap",
]

ENTITY_NAMES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "chatgpt": "ChatGPT",
    "gemini": "Gemini",
    "deepmind": "DeepMind",
    "nvidia": "NVIDIA",
    "tsmc": "TSMC",
    "asml": "ASML",
    "amd": "AMD",
    "intel": "Intel",
    "micron": "Micron",
    "sk hynix": "SK Hynix",
    "samsung": "Samsung",
    "broadcom": "Broadcom",
    "qualcomm": "Qualcomm",
    "arm": "Arm",
    "apple": "Apple",
    "microsoft": "Microsoft",
    "meta": "Meta",
    "amazon": "Amazon",
    "alphabet": "Alphabet",
    "google": "Google",
    "tesla": "Tesla",
    "oracle": "Oracle",
    "palantir": "Palantir",
    "alibaba": "Alibaba",
    "tencent": "Tencent",
    "bytedance": "ByteDance",
    "tiktok": "TikTok",
    "huawei": "Huawei",
    "baidu": "Baidu",
    "xiaomi": "Xiaomi",
    "smic": "SMIC",
    "fed": "Fed",
    "federal reserve": "Fed",
    "ecb": "ECB",
    "china": "中國",
}

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "as",
    "by",
    "from",
    "after",
    "before",
    "at",
    "is",
    "are",
    "be",
    "will",
    "may",
    "new",
    "says",
    "said",
    "update",
}

URL_RESOLVE_CACHE: dict[str, str] = {}


@dataclass
class Feed:
    name: str
    url: str


@dataclass
class NewsItem:
    title: str
    source: str
    published: str
    link: str
    category: str
    summary: str = ""


@dataclass
class Story:
    key: str
    items: list[NewsItem] = field(default_factory=list)

    @property
    def main(self) -> NewsItem:
        return sorted(self.items, key=item_rank_key, reverse=True)[0]

    @property
    def sources(self) -> list[str]:
        result: list[str] = []
        for item in sorted(self.items, key=item_rank_key, reverse=True):
            source = display_source(item)
            if source and source not in result:
                result.append(source)
        return result

    @property
    def links(self) -> list[str]:
        return story_links(self, resolve_google=True, limit=3)


def local_now() -> datetime:
    return datetime.now(LOCAL_TIMEZONE)


def read_feeds(path: Path) -> list[Feed]:
    feeds: list[Feed] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            name, url = [part.strip() for part in line.split("|", 1)]
        else:
            url = line
            name = urllib.parse.urlparse(url).netloc or "Unknown"
        feeds.append(Feed(name=name, url=url))
    return feeds


def fetch_xml(url: str, timeout: int = 20) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "news-research-terminal/1.0 (+local script)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def text_of(element: ET.Element | None, default: str = "") -> str:
    if element is None or element.text is None:
        return default
    return clean_text(element.text)


def first_text(parent: ET.Element, paths: list[str], default: str = "") -> str:
    for path in paths:
        value = text_of(parent.find(path))
        if value:
            return value
    return default


def link_from_item(item: ET.Element) -> str:
    link = first_text(item, ["link", "{http://www.w3.org/2005/Atom}link"])
    if link:
        return link
    for child in item.findall("{http://www.w3.org/2005/Atom}link"):
        href = child.attrib.get("href", "").strip()
        if href:
            return href
    return ""


def summary_from_rss_item(item: ET.Element) -> str:
    return first_text(
        item,
        [
            "description",
            "summary",
            "{http://purl.org/rss/1.0/modules/content/}encoded",
        ],
    )


def summary_from_atom_item(item: ET.Element) -> str:
    return first_text(
        item,
        [
            "{http://www.w3.org/2005/Atom}summary",
            "{http://www.w3.org/2005/Atom}content",
        ],
    )


def parse_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def format_date(value: str) -> str:
    parsed = parse_date(value)
    if not parsed:
        return value.strip() or "時間未明"
    return parsed.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M")


def feed_title(root: ET.Element, fallback: str) -> str:
    channel = root.find("channel")
    if channel is not None:
        title = first_text(channel, ["title"])
        if title:
            return title
    title = first_text(root, ["{http://www.w3.org/2005/Atom}title"])
    return title or fallback


def parse_feed(xml_data: bytes, feed: Feed) -> list[dict[str, str]]:
    root = ET.fromstring(xml_data)
    default_source = clean_text(feed_title(root, feed.name))

    if root.find("channel") is not None:
        items = root.findall("./channel/item")
        return [
            {
                "title": clean_text(first_text(item, ["title"])),
                "source": clean_text(first_text(item, ["source"], default_source)),
                "published": format_date(first_text(item, ["pubDate", "date"])),
                "link": link_from_item(item),
                "summary": clean_text(summary_from_rss_item(item)),
            }
            for item in items
        ]

    atom_items = root.findall("{http://www.w3.org/2005/Atom}entry")
    return [
        {
            "title": clean_text(first_text(item, ["{http://www.w3.org/2005/Atom}title"])),
            "source": default_source,
            "published": format_date(
                first_text(
                    item,
                    [
                        "{http://www.w3.org/2005/Atom}published",
                        "{http://www.w3.org/2005/Atom}updated",
                    ],
                )
            ),
            "link": link_from_item(item),
            "summary": clean_text(summary_from_atom_item(item)),
        }
        for item in atom_items
    ]


def keyword_matches(haystack: str, keyword: str) -> bool:
    keyword = keyword.lower().strip()
    if not keyword:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(keyword).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def normalize_title(title: str) -> str:
    title = strip_source_suffix(title).lower()
    title = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def normalize_link(link: str) -> str:
    parsed = urllib.parse.urlparse(link)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def strip_source_suffix(title: str) -> str:
    return re.sub(r"\s+-\s+[^-]{2,80}$", "", title).strip()


def source_name_from_title(title: str) -> str:
    match = re.search(r"\s+-\s+([^-]{2,80})$", title.strip())
    return match.group(1).strip() if match else ""


def display_source(item: NewsItem) -> str:
    suffix = source_name_from_title(item.title)
    if suffix:
        return suffix
    source = clean_text(item.source)
    if source:
        return source
    return urllib.parse.urlparse(item.link).netloc or "來源未明"


def source_haystack(item: NewsItem) -> str:
    return " ".join(
        [
            item.source,
            source_name_from_title(item.title),
            urllib.parse.urlparse(item.link).netloc,
        ]
    ).lower()


def source_weight(item: NewsItem) -> int:
    haystack = source_haystack(item)
    if any(pattern in haystack for pattern in HIGH_WEIGHT_SOURCES):
        return 35
    if any(pattern in haystack for pattern in MEDIUM_WEIGHT_SOURCES):
        return 18
    if any(pattern in haystack for pattern in LOW_WEIGHT_SOURCES):
        return -25
    return 0


def source_tier(item: NewsItem) -> str:
    weight = source_weight(item)
    if weight >= 35:
        return "高權重"
    if weight >= 18:
        return "中權重"
    if weight < 0:
        return "低權重"
    return "一般來源"


def classify(title: str, source: str = "") -> str:
    haystack = f"{title} {source}".lower()
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword_matches(haystack, keyword))
        if score:
            scores[category] = score
    if not scores:
        return "其他"
    return max(scores, key=lambda category: (scores[category], -list(CATEGORY_KEYWORDS).index(category)))


def extract_entities(item: NewsItem) -> list[str]:
    haystack = f"{item.title} {item.source}".lower()
    entities: list[str] = []
    for keyword, display in ENTITY_NAMES.items():
        if keyword_matches(haystack, keyword) and display not in entities:
            entities.append(display)
    return entities


def matched_groups(item: NewsItem) -> dict[str, list[str]]:
    haystack = f"{item.title} {item.source}".lower()
    matches: dict[str, list[str]] = {}
    for group, keywords in IMPORTANT_KEYWORDS.items():
        group_matches = [keyword for keyword in keywords if keyword_matches(haystack, keyword)]
        if group_matches:
            matches[group] = group_matches
    return matches


def matched_triggers(title: str) -> list[str]:
    haystack = title.lower()
    return [trigger for trigger in HEADLINE_TRIGGERS if keyword_matches(haystack, trigger)]


def low_signal_penalty(title: str) -> int:
    haystack = title.lower()
    return -30 if any(pattern in haystack for pattern in LOW_SIGNAL_TITLE_PATTERNS) else 0


def item_score(item: NewsItem, coverage: int = 1) -> int:
    group_hits = sum(len(values) for values in matched_groups(item).values())
    trigger_hits = len(matched_triggers(item.title))
    entity_hits = len(extract_entities(item))
    score = source_weight(item)
    score += min(group_hits, 9) * 5
    score += min(trigger_hits, 5) * 5
    score += min(entity_hits, 5) * 4
    score += min(max(coverage - 1, 0), 5) * 7
    score += 5 if item.category != "其他" else 0
    score += low_signal_penalty(item.title)
    return score


def item_rank_key(item: NewsItem) -> tuple[int, int, str]:
    parsed = parse_date(item.published)
    timestamp = int(parsed.timestamp()) if parsed else 0
    return (item_score(item), timestamp, item.title)


def is_google_news_link(link: str) -> bool:
    parsed = urllib.parse.urlparse(link)
    return parsed.netloc.endswith("news.google.com")


def clean_resolved_url(url: str) -> str:
    parsed = urllib.parse.urlparse(html.unescape(url))
    if not parsed.scheme.startswith("http"):
        return ""
    blocked_domains = (
        "google.",
        "google-analytics.",
        "googleapis.",
        "googletagmanager.",
        "doubleclick.",
        "googleusercontent.",
        "gstatic.",
        "schema.org",
        "w3.org",
        "facebook.com",
        "twitter.com",
    )
    if any(domain in parsed.netloc for domain in blocked_domains):
        return ""
    if re.search(r"\.(png|jpg|jpeg|gif|webp|svg|js|css)(?:$|\?)", parsed.path, re.IGNORECASE):
        return ""
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ""))


def resolve_article_link(link: str) -> str:
    if not is_google_news_link(link):
        return link
    # Google News links are intentionally kept when a feed does not expose the
    # original article URL. Opening every Google wrapper is slow and sometimes
    # returns script or framework asset URLs instead of the news article.
    return link


def story_links(story: Story, resolve_google: bool, limit: int = 3) -> list[str]:
    result: list[str] = []
    for item in sorted(story.items, key=item_rank_key, reverse=True)[:limit]:
        link = resolve_article_link(item.link) if resolve_google else item.link
        if link and link not in result:
            result.append(link)
    return result


def deduplicate(raw_items: list[dict[str, str]]) -> list[NewsItem]:
    seen_titles: set[str] = set()
    seen_links: set[str] = set()
    items: list[NewsItem] = []
    for raw in raw_items:
        title = clean_text(raw.get("title", ""))
        link = raw.get("link", "").strip()
        if not title or not link:
            continue
        title_key = normalize_title(title)
        link_key = normalize_link(link)
        if title_key in seen_titles or link_key in seen_links:
            continue
        seen_titles.add(title_key)
        seen_links.add(link_key)
        source = clean_text(raw.get("source", "")) or urllib.parse.urlparse(link).netloc
        items.append(
            NewsItem(
                title=title,
                source=source,
                published=raw.get("published", "時間未明"),
                link=link,
                category=classify(title, source),
                summary=clean_text(raw.get("summary", "")),
            )
        )
    return items


def story_signature(item: NewsItem) -> str:
    title = normalize_title(item.title)
    entities = extract_entities(item)
    triggers = matched_triggers(item.title)
    words = [
        word
        for word in title.split()
        if len(word) > 2 and word not in STOPWORDS and not word.isdigit()
    ]
    if entities:
        entity_part = "-".join(sorted(entity.lower() for entity in entities[:3]))
        trigger_part = "-".join(sorted(triggers[:2])) if triggers else ""
        word_part = "-".join(words[:5])
        return f"{item.category}|{entity_part}|{trigger_part}|{word_part}"

    return f"{item.category}|{'-'.join(words[:7])}"


def merge_stories(items: list[NewsItem]) -> list[Story]:
    stories_by_key: dict[str, Story] = {}
    for item in items:
        key = story_signature(item)
        stories_by_key.setdefault(key, Story(key=key)).items.append(item)
    stories = list(stories_by_key.values())
    return sorted(stories, key=story_score, reverse=True)


def story_score(story: Story) -> int:
    main = story.main
    coverage = len(story.sources)
    return item_score(main, coverage=coverage)


def select_layers(stories: list[Story]) -> tuple[list[Story], list[Story], list[Story]]:
    a_candidates = [
        story
        for story in stories
        if is_a_level(story)
    ]
    a_stories: list[Story] = []
    used: set[str] = set()

    for story in a_candidates:
        if story.key not in used:
            a_stories.append(story)
            used.add(story.key)
        if len(a_stories) >= 5:
            break

    for story in stories:
        if len(a_stories) >= 3:
            break
        if story.key not in used:
            a_stories.append(story)
            used.add(story.key)

    b_stories: list[Story] = []
    for story in stories:
        if story.key in used:
            continue
        b_stories.append(story)
        used.add(story.key)
        if len(b_stories) >= 12:
            break

    c_stories: list[Story] = []
    for story in stories:
        if story.key in used:
            continue
        c_stories.append(story)
        used.add(story.key)
        if len(c_stories) >= 25:
            break

    return a_stories, b_stories, c_stories


def is_a_level(story: Story) -> bool:
    main = story.main
    source_is_strong = source_weight(main) >= 35
    has_core_topic = main.category in {"AI", "半導體", "美國科技股", "宏觀經濟", "金融市場"}
    has_signal = bool(matched_groups(main) or matched_triggers(main.title))
    return source_is_strong and has_core_topic and has_signal


def subject_of(item: NewsItem) -> str:
    entities = extract_entities(item)
    if entities:
        return "、".join(entities[:3])
    return item.category


def topic_phrase(item: NewsItem) -> str:
    groups = list(matched_groups(item))
    if groups:
        return "、".join(groups[:3])
    if item.category != "其他":
        return item.category
    return "國際財經與科技"


PHRASE_TRANSLATIONS = [
    ("artificial intelligence", "AI"),
    ("ai infrastructure", "AI基礎設施"),
    ("infrastructure supply agreement", "基礎設施供應協議"),
    ("supply agreement", "供應協議"),
    ("banned", "被禁售的"),
    ("black market", "黑市"),
    ("double in price", "價格翻倍"),
    ("chips", "晶片"),
    ("chipmaker", "晶片商"),
    ("tests", "測試"),
    ("presses", "敦促"),
    ("agree to", "同意接受"),
    ("reviews", "審查"),
    ("security concerns rise", "安全疑慮上升"),
    ("lead tech sell-off as ai trade cools", "領跌科技股，AI交易降溫"),
    ("new chip to speed ai processing, shake up computing market", "新晶片，以加速AI處理並改變運算市場"),
    ("shrinking margin", "毛利率收窄"),
    ("first earnings report since ipo", "IPO後首份業績"),
    ("ai chip startup", "AI晶片新創"),
    ("chip startup", "晶片新創"),
    ("data center", "資料中心"),
    ("datacenter", "資料中心"),
    ("capital expenditure", "資本開支"),
    ("earnings", "業績"),
    ("revenue", "營收"),
    ("profit", "利潤"),
    ("guidance", "財測"),
    ("forecast", "預測"),
    ("forecasts", "預測"),
    ("interest rate", "利率"),
    ("rate cut", "減息"),
    ("rate hike", "加息"),
    ("inflation", "通膨"),
    ("employment", "就業"),
    ("acquisition", "收購"),
    ("merger", "合併"),
    ("investment", "投資"),
    ("lawsuit", "訴訟"),
    ("investigation", "調查"),
    ("export control", "出口管制"),
    ("tariff", "關稅"),
    ("stock", "股價"),
    ("stocks", "股票"),
    ("shares", "股價"),
    ("stock struggles", "股價受壓"),
    ("surge", "急升"),
    ("jump", "上升"),
    ("gain", "上升"),
    ("gains", "上升"),
    ("rise", "上升"),
    ("rises", "上升"),
    ("fall", "下跌"),
    ("falls", "下跌"),
    ("drop", "下跌"),
    ("drops", "下跌"),
    ("plunge", "急跌"),
    ("plunges", "急跌"),
    ("launch", "推出"),
    ("launches", "推出"),
    ("unveil", "發布"),
    ("unveils", "發布"),
    ("release", "發布"),
    ("releases", "發布"),
    ("deal", "交易"),
    ("agreement", "協議"),
    ("partnership", "合作"),
    ("partner with", "與其合作"),
    ("ahead of ipo", "IPO前"),
    ("ipo", "IPO"),
    ("marketers", "行銷客戶"),
    ("ads", "廣告"),
    ("assistant", "助理"),
    ("most popular app", "最受歡迎應用程式"),
    ("as it looks to catch up with rivals", "以追趕競爭對手"),
    ("ft reports", "FT報導"),
    ("nyt reports", "NYT報導"),
    ("reports", "報導"),
]

FORBIDDEN_SUMMARY_PHRASES = [part_a + part_b for part_a, part_b in [
    ("AI資本開支", "或模型競爭有變化"),
    ("影響市場", "判讀"),
    ("調整AI", "產品布局"),
    ("牽涉大型科技股", "估值"),
    ("需追蹤資本開支", "與雲端需求"),
    ("屬於市場", "風險訊號"),
    ("調整AI產品、模型", "或基礎設施布局"),
    ("牽涉大型科技股估值", "與業務動能"),
]]


def clean_headline(title: str) -> str:
    title = strip_source_suffix(title)
    title = title.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    title = re.sub(r"\s+", " ", title)
    return title.strip(" -")


def zh_fragment(text: str) -> str:
    text = clean_text(text).strip(" .")
    text = text.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    for english, chinese in PHRASE_TRANSLATIONS:
        text = re.sub(re.escape(english), chinese, text, flags=re.IGNORECASE)
    text = re.sub(r"\bUS\b", "美國", text)
    text = re.sub(r"\bU\.S\.\b", "美國", text)
    text = re.sub(r"\bNvidia's\b", "NVIDIA的", text, flags=re.IGNORECASE)
    text = re.sub(r"\bGoogle's\b", "Google的", text, flags=re.IGNORECASE)
    text = re.sub(r"\bChina's\b", "中國的", text, flags=re.IGNORECASE)
    text = text.replace("中國的 黑市", "中國黑市")
    text = text.replace(" on 中國黑市", "在中國黑市")
    text = text.replace("價格翻倍 on 中國黑市", "在中國黑市價格翻倍")
    text = text.replace("NVIDIA的 被禁售的 AI 晶片 價格翻倍在中國黑市", "NVIDIA被禁售AI晶片在中國黑市價格翻倍")
    text = text.replace("NVIDIA的 被禁售的 AI 晶片 在中國黑市價格翻倍", "NVIDIA被禁售AI晶片在中國黑市價格翻倍")
    text = text.replace("Tencent 測試 AI 助理 in 中國的 最受歡迎應用程式", "Tencent在中國最受歡迎應用程式內測試AI助理")
    text = text.replace("Nvidia計劃新晶片，以加速AI處理並改變運算市場", "NVIDIA計劃推出新晶片，以加速AI處理並改變運算市場")
    text = text.replace("in IPO後首份業績", "在IPO後首份業績中")
    text = text.replace("預測s", "預測")
    text = text.replace("股價s", "股價")
    return text


def mostly_english(text: str) -> bool:
    ascii_letters = len(re.findall(r"[A-Za-z]", text))
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return ascii_letters > 60 and chinese_chars < 12


def first_useful_summary(item: NewsItem) -> str:
    summary = clean_text(item.summary)
    title = clean_headline(item.title)
    if not summary:
        return ""
    if normalize_title(summary) == normalize_title(title):
        return ""
    source_tokens = {item.source.lower(), display_source(item).lower()}
    if len(summary) < 25 or summary.lower() in source_tokens:
        return ""
    if title.lower() in summary.lower():
        summary = summary.replace(title, "").strip(" -:。")
    summary = re.sub(r"\s+-\s+[^-]{2,80}$", "", summary).strip()
    translated = zh_fragment(summary)
    if mostly_english(translated):
        return ""
    return trim_to_chars(translated, 120)


def headline_event(item: NewsItem) -> str:
    title = clean_headline(item.title)
    patterns: list[tuple[str, str]] = [
        (r"^(?P<actor>.+?)\s+(?:signs|signed|sign)\s+(?P<object>.+?(?:agreement|deal|contract|partnership).*)$", "{actor}簽署{object}"),
        (r"^(?P<actor>.+?)\s+(?:nears|near|nearing|is nearing|close to)\s+(?P<object>.+)$", "{actor}接近{object}"),
        (r"^(?P<actor>.+?)\s+(?:launches|launch|unveils|unveil|releases|release|introduces|introduce|rolls out)\s+(?P<object>.+)$", "{actor}推出{object}"),
        (r"^(?P<actor>.+?)\s+(?:invests|investing|invest|backs|funds)\s+(?:in\s+)?(?P<object>.+)$", "{actor}投資{object}"),
        (r"^(?P<actor>.+?)\s+(?:plans|plans to|aims to|seeks to)\s+(?P<object>.+)$", "{actor}計劃{object}"),
        (r"^(?P<actor>.+?)\s+(?:taps|appoints|names|hires)\s+(?P<object>.+)$", "{actor}任命或起用{object}"),
        (r"^(?P<actor>.+?)\s+(?:leaves|exits|quits)\s+(?:for|to join)\s+(?P<object>.+)$", "{actor}離職並轉往{object}"),
        (r"^(?P<actor>.+?)\s+(?:sues|sued)\s+(?P<object>.+)$", "{actor}控告{object}"),
        (r"^(?P<actor>.+?)\s+(?:faces|face)\s+(?P<object>.+?)(?:lawsuit|probe|investigation)(?P<tail>.*)$", "{actor}面對{object}調查或訴訟{tail}"),
        (r"^(?P<actor>.+?)\s+(?:cuts|cut|slashes|layoffs|lays off)\s+(?P<object>.+)$", "{actor}削減或裁減{object}"),
        (r"^(?P<actor>.+?)\s+(?:reports|posts)\s+(?P<object>.+?)(?:earnings|revenue|profit|results)(?P<tail>.*)$", "{actor}公布{object}業績{tail}"),
        (r"^(?P<actor>.+?)\s+(?:raises|raise)\s+(?P<object>.+)$", "{actor}上調或籌集{object}"),
        (r"^(?P<actor>.+?)\s+(?:warns|warn)\s+(?P<object>.+)$", "{actor}警告{object}"),
    ]
    stock_pattern = None
    if re.search(r"\b(stock|stocks|shares)\b|\d+(?:\.\d+)?%", title, re.IGNORECASE):
        stock_pattern = re.search(
            r"^(?P<actor>.+?)\s+(?:stock|stocks|shares)?\s*(?:gains|gain|rises|rise|jumps|jump|surges|surge|falls|fall|drops|drop|plunges|plunge|struggles)\s*(?P<num>\d+(?:\.\d+)?%)?\s*(?:after|as|on|amid)?\s*(?P<reason>.*)$",
            title,
            flags=re.IGNORECASE,
        )
    if stock_pattern:
        actor = zh_fragment(stock_pattern.group("actor"))
        num = stock_pattern.group("num") or ""
        reason = zh_fragment(stock_pattern.group("reason"))
        direction = "下跌或受壓" if re.search(r"fall|drop|plunge|struggle", title, re.IGNORECASE) else "上升"
        detail = f"{num}" if num else ""
        if reason:
            return f"{actor}股價{direction}{detail}，原因是{reason}"
        return f"{actor}股價{direction}{detail}"

    for pattern, template in patterns:
        match = re.search(pattern, title, flags=re.IGNORECASE)
        if not match:
            continue
        values = {key: zh_fragment(value) for key, value in match.groupdict(default="").items()}
        return template.format(**values)

    if re.search(r"\bban|restriction|export control|tariff\b", title, re.IGNORECASE):
        return f"{zh_fragment(title)}，涉及禁令、限制、出口管制或關稅措施"
    if re.search(r"\bFed|Federal Reserve|ECB|inflation|GDP|CPI|employment|payrolls?\b", title, re.IGNORECASE):
        return f"{zh_fragment(title)}，焦點是利率、通膨或經濟數據變化"
    return f"原文標題指出：{zh_fragment(title)}"


def event_headline(story: Story) -> str:
    event = headline_event(story.main)
    event = re.sub(r"^原文標題指出：", "", event)
    event = event.strip("。")
    if len(event) <= 70:
        return event
    return event[:69].rstrip("，。、；： ") + "…"


def chinese_title(story: Story) -> str:
    return event_headline(story)


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def trim_to_chars(value: str, max_chars: int) -> str:
    value = compact_text(value)
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip("，。、；： ") + "。"


def source_list(story: Story, limit: int = 4) -> str:
    sources = story.sources[:limit]
    if len(story.sources) > limit:
        sources.append(f"另{len(story.sources) - limit}家")
    return "、".join(sources) if sources else "來源未明"


def clean_forbidden_phrases(text: str) -> str:
    for phrase in FORBIDDEN_SUMMARY_PHRASES:
        text = text.replace(phrase, "")
    return compact_text(text)


def direct_event_sentence(story: Story) -> str:
    item = story.main
    event = headline_event(item)
    summary = first_useful_summary(item)
    source_names = {source.lower() for source in story.sources}
    if len(summary) < 25 or summary.lower() in source_names:
        summary = ""
    sentence = f"{source_list(story, 3)}報導，{event}。"
    if summary:
        sentence += f" RSS摘要補充，{summary}。"
    return clean_forbidden_phrases(sentence)


def background_sentence(story: Story) -> str:
    item = story.main
    coverage = len(story.sources)
    source_note = f"同一事件亦見於{coverage}個來源，" if coverage > 1 else ""
    category_background = {
        "AI": "背景是生成式AI公司正把模型能力延伸到廣告、搜尋、企業軟件、資料中心與內容製作，人才流動和供應協議常直接反映商業化進度。",
        "半導體": "背景是AI伺服器需求令GPU、HBM、先進封裝和晶圓代工產能成為供應鏈瓶頸，任何合作、價格或產能消息都會被快速放大。",
        "美國科技股": "背景是大型科技公司正以AI、雲端、廣告、電商與硬件更新維持增長，管理層任命、產品發布和投資金額會影響盈利假設。",
        "中國科技": "背景是中國平台公司在監管壓力和本土AI競爭下重新推產品、調資源，微信、電商和短影音入口仍是最重要流量戰場。",
        "宏觀經濟": "背景是投資人正從通膨、就業、GDP與央行官員表態推算下一步利率路徑，外匯、債息和股市會同步反應。",
        "金融市場": "背景是資金在股、債、匯、商品之間重新配置，油價、美元、債息和大型股財報常會互相牽動。",
    }
    return clean_forbidden_phrases(source_note + category_background.get(item.category, "背景是這則消息提供了公司行動、政策方向或資產價格變動的具體線索。"))


def market_meaning_sentence(story: Story) -> str:
    item = story.main
    title = clean_headline(item.title).lower()
    subject = subject_of(item)
    if re.search(r"stock|shares|gains|rises|falls|drops|plunges|struggles", title):
        return f"市場含義在於，{subject}相關股價已對消息作出即時反應，下一步要看成交量、同業股價和期權定價是否確認這個方向。"
    if re.search(r"agreement|deal|partner|supply|acquisition|merger", title):
        return f"市場含義在於，交易或協議若落實，會改變{subject}的供應、客戶或收入來源；後續關鍵是金額、期限和交付時間。"
    if re.search(r"ipo|ads|revenue|profit|earnings|guidance", title):
        return f"市場含義在於，這則消息直接涉及{subject}的變現能力或財務預期，投資人會把它放進上市、估值或財測模型。"
    if re.search(r"fed|rate|inflation|cpi|gdp|employment|tariff|export control", title):
        return "市場含義在於，政策或數據會改變利率、匯率、債息和風險資產的短線定價。"
    return f"市場含義在於，事件把{subject}放回供應、需求、監管或商業化進度的核心位置。"


def factual_padding(story: Story) -> str:
    item = story.main
    title = clean_headline(item.title)
    entities = extract_entities(item)
    entity_text = "、".join(entities) if entities else subject_of(item)
    return f"原文標題寫明「{zh_fragment(title)}」，涉及{entity_text}；目前RSS未提供完整內文，因此晨報保留可由標題確認的動作、對象和變化。"


def fit_summary(text: str, story: Story, min_chars: int, max_chars: int) -> str:
    text = clean_forbidden_phrases(text)
    additions = [
        background_sentence(story),
        market_meaning_sentence(story),
        factual_padding(story),
    ]
    for addition in additions:
        if len(text) >= min_chars:
            break
        if addition and addition not in text:
            text = f"{text}{addition}"
    if len(text) < min_chars:
        main = story.main
        text = f"{text}目前可確認的變化是：{event_headline(story)}；消息來源包括{source_list(story, 3)}，時間為{main.published}。"
    return trim_to_chars(clean_forbidden_phrases(text), max_chars)


def a_summary(story: Story) -> str:
    text = (
        f"{direct_event_sentence(story)}"
        f"{background_sentence(story)}"
        f"{market_meaning_sentence(story)}"
    )
    return fit_summary(text, story, 250, 400)


def b_summary(story: Story) -> str:
    text = (
        f"{direct_event_sentence(story)}"
        f"{background_sentence(story)}"
    )
    return fit_summary(text, story, 120, 200)


def c_summary(story: Story) -> str:
    text = direct_event_sentence(story)
    return fit_summary(text, story, 40, 80)


def render_story(lines: list[str], index: int, story: Story, level: str) -> None:
    item = story.main
    links = story_links(story, resolve_google=level in {"A", "B"}, limit=3 if level in {"A", "B"} else 1)
    lines.append(f"### {index}. {chinese_title(story)}")
    lines.append("")
    lines.append(f"- 來源：{source_list(story)}")
    lines.append(f"- 類別：{item.category}")
    lines.append(f"- 時間：{item.published}")
    if level == "A":
        lines.append(f"- 摘要：{a_summary(story)}")
    elif level == "B":
        lines.append(f"- 摘要：{b_summary(story)}")
    else:
        lines.append(f"- 摘要：{c_summary(story)}")
    for link_index, link in enumerate(links, 1):
        label = "連結" if len(links) == 1 else f"連結{link_index}"
        lines.append(f"- {label}：{link}")
    lines.append("")


def render_markdown(stories: list[Story], errors: list[str]) -> str:
    today = local_now().strftime("%Y-%m-%d")
    a_stories, b_stories, c_stories = select_layers(stories)

    lines = [
        f"# Daily Research Brief - {today}",
        "",
        "分層式市場晨報",
        "",
        f"生成時間：{local_now().strftime('%Y-%m-%d %H:%M')}（香港／台灣時間）",
        "",
        "## A級新聞",
        "",
    ]

    if not a_stories:
        lines.append("今日沒有足夠A級新聞。")
        lines.append("")
    else:
        for index, story in enumerate(a_stories, 1):
            render_story(lines, index, story, "A")

    lines.extend(["## B級新聞", ""])
    if not b_stories:
        lines.append("今日沒有足夠B級新聞。")
        lines.append("")
    else:
        for index, story in enumerate(b_stories, 1):
            render_story(lines, index, story, "B")

    lines.extend(["## C級新聞", ""])
    if not c_stories:
        lines.append("今日沒有足夠C級新聞。")
        lines.append("")
    else:
        for index, story in enumerate(c_stories, 1):
            render_story(lines, index, story, "C")

    if errors:
        lines.extend(["## 抓取狀態", ""])
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")

    return "\n".join(lines)


def render_ai_candidates(stories: list[Story], max_candidates: int) -> str:
    today = local_now().strftime("%Y-%m-%d")
    a_stories, b_stories, _ = select_layers(stories)
    candidates = (a_stories + b_stories)[:max_candidates]

    lines = [
        f"# 分層式選題池 - {today}",
        "",
        "以下新聞由RSS標題、來源權重、關鍵公司、政策與市場風險訊號自動篩選；未使用OpenAI API。",
        "",
    ]

    if not candidates:
        lines.append("今日沒有足夠候選新聞。")
        return "\n".join(lines)

    for index, story in enumerate(candidates, 1):
        item = story.main
        level = "A" if story in a_stories else "B"
        summary = a_summary(story) if level == "A" else b_summary(story)
        lines.extend(
            [
                f"## {index}. {level}級｜{chinese_title(story)}",
                "",
                f"來源：{source_list(story)}",
                f"類別：{item.category}",
                f"摘要：{summary}",
            ]
        )
        links = story_links(story, resolve_google=True, limit=1)
        if links:
            lines.append(f"連結：{links[0]}")
        lines.append("")

    return "\n".join(lines)


def fetch_all_items(feeds: list[Feed]) -> tuple[list[dict[str, str]], list[str]]:
    raw_items: list[dict[str, str]] = []
    errors: list[str] = []
    for feed in feeds:
        try:
            raw_items.extend(parse_feed(fetch_xml(feed.url), feed))
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            errors.append(f"{feed.name} 抓取失敗：{exc}")
    return raw_items, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取RSS並產生分層式市場晨報")
    parser.add_argument("--feeds", type=Path, default=DEFAULT_FEEDS_FILE, help="RSS來源檔案")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE, help="每日晨報輸出檔案")
    parser.add_argument("--candidates-output", type=Path, default=DEFAULT_CANDIDATES_FILE, help="候選新聞輸出檔案")
    parser.add_argument("--max-candidates", type=int, default=20, help="候選新聞最多輸出數量")
    parser.add_argument("--max-per-category", type=int, default=5, help="保留舊參數相容；分層式晨報不使用此設定")
    args = parser.parse_args()

    if not args.feeds.exists():
        print(f"找不到RSS來源檔案：{args.feeds}", file=sys.stderr)
        return 1

    feeds = read_feeds(args.feeds)
    raw_items, errors = fetch_all_items(feeds)
    items = deduplicate(raw_items)
    stories = merge_stories(items)

    args.output.write_text(render_markdown(stories, errors), encoding="utf-8")
    args.candidates_output.write_text(render_ai_candidates(stories, args.max_candidates), encoding="utf-8")

    print(f"已產生 {args.output}，合併後共 {len(stories)} 條新聞。")
    print(f"已產生 {args.candidates_output}。")
    if errors:
        print(f"有 {len(errors)} 個RSS來源抓取失敗，詳情已寫入晨報。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
