from __future__ import annotations

import argparse
import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FEEDS_FILE = BASE_DIR / "feeds.txt"
DEFAULT_OUTPUT_FILE = BASE_DIR / "daily_brief.md"
DEFAULT_CANDIDATES_FILE = BASE_DIR / "ai_candidates.md"
LOCAL_TIMEZONE = timezone(timedelta(hours=8), "Asia/Hong_Kong")


def local_now() -> datetime:
    return datetime.now(LOCAL_TIMEZONE)

# 修改分類時，主要改這個 dictionary 就好。
# 程式會依照這裡的順序判斷；若同一則新聞命中多個分類，命中較多關鍵字者優先。
CATEGORY_KEYWORDS = {
    "AI": [
        "ai",
        "artificial intelligence",
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "deepmind",
        "chatgpt",
        "copilot",
        "llm",
        "llms",
        "large language model",
        "generative ai",
        "machine learning",
        "foundation model",
        "agent",
        "agents",
        "agentic",
        "ai model",
        "ai startup",
        "人工智能",
        "人工智慧",
        "大模型",
        "生成式 ai",
        "生成式人工智能",
    ],
    "半導體": [
        "semiconductor",
        "semiconductors",
        "chip",
        "chips",
        "tsmc",
        "nvidia",
        "nvda",
        "amd",
        "intel",
        "asml",
        "qualcomm",
        "broadcom",
        "micron",
        "samsung electronics",
        "sk hynix",
        "arm",
        "fab",
        "foundry",
        "wafer",
        "hbm",
        "gpu",
        "gpus",
        "chipmaking",
        "chipmaker",
        "advanced packaging",
        "半導體",
        "晶片",
        "台積電",
        "英偉達",
        "輝達",
        "三星電子",
    ],
    "美國科技股": [
        "nasdaq",
        "nasdaq 100",
        "magnificent seven",
        "mag 7",
        "apple",
        "aapl",
        "microsoft",
        "msft",
        "alphabet",
        "google",
        "googl",
        "goog",
        "amazon",
        "amzn",
        "meta",
        "tesla",
        "tsla",
        "netflix",
        "nflx",
        "salesforce",
        "palantir",
        "oracle",
        "adobe",
        "snowflake",
        "美股",
        "科技股",
        "七巨頭",
    ],
    "中國科技": [
        "china tech",
        "chinese tech",
        "alibaba",
        "baba",
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
        "kuaishou",
        "deepseek",
        "china ai",
        "chinese ai",
        "hong kong tech",
        "中國科技",
        "阿里巴巴",
        "騰訊",
        "字節跳動",
        "華為",
        "百度",
        "小米",
        "中芯",
        "美團",
        "快手",
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
        "monetary policy",
        "interest rate",
        "rate cut",
        "rate hike",
        "inflation",
        "cpi",
        "ppi",
        "gdp",
        "pmi",
        "jobs report",
        "nonfarm payrolls",
        "payroll",
        "unemployment",
        "recession",
        "soft landing",
        "tariff",
        "trade war",
        "fiscal policy",
        "deficit",
        "宏觀",
        "通脹",
        "通膨",
        "利率",
        "聯儲",
        "聯準會",
        "央行",
        "貨幣政策",
        "經濟成長",
    ],
    "金融市場": [
        "stock market",
        "stocks",
        "s&p 500",
        "spx",
        "dow",
        "dow jones",
        "bond",
        "bonds",
        "treasury",
        "treasuries",
        "yield",
        "yields",
        "dollar",
        "us dollar",
        "yen",
        "euro",
        "crude oil",
        "oil price",
        "oil prices",
        "oil trade",
        "brent",
        "wti",
        "gold",
        "bitcoin",
        "crypto",
        "cryptocurrency",
        "forex",
        "etf",
        "earnings",
        "ipo",
        "vix",
        "volatility",
        "金融市場",
        "股市",
        "債券",
        "美元",
        "日圓",
        "黃金",
        "比特幣",
        "加密貨幣",
    ],
    "其他": [],
}

IMPORTANT_KEYWORDS = {
    "AI": [
        "OpenAI",
        "Anthropic",
        "ChatGPT",
        "Gemini",
        "DeepMind",
        "LLM",
        "Agent",
        "AI",
    ],
    "半導體": [
        "NVIDIA",
        "TSMC",
        "ASML",
        "AMD",
        "Intel",
        "Micron",
        "SK Hynix",
        "chip",
        "semiconductor",
        "GPU",
    ],
    "大型科技": [
        "Apple",
        "Microsoft",
        "Meta",
        "Amazon",
        "Alphabet",
        "Google",
        "Tesla",
    ],
    "宏觀經濟": [
        "Fed",
        "Federal Reserve",
        "ECB",
        "interest rate",
        "inflation",
        "GDP",
        "employment",
    ],
    "市場": [
        "earnings",
        "IPO",
        "M&A",
        "acquisition",
        "tariff",
        "China",
        "trade",
    ],
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
    "apple": "Apple",
    "microsoft": "Microsoft",
    "meta": "Meta",
    "amazon": "Amazon",
    "alphabet": "Alphabet",
    "google": "Google",
    "tesla": "Tesla",
    "alibaba": "阿里巴巴",
    "tencent": "騰訊",
    "huawei": "華為",
    "baidu": "百度",
    "xiaomi": "小米",
    "fed": "Fed",
    "federal reserve": "Fed",
    "ecb": "ECB",
    "china": "中國",
}


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


def text_of(element: ET.Element | None, default: str = "") -> str:
    if element is None or element.text is None:
        return default
    return html.unescape(element.text.strip())


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


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


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
        return value.strip() or "時間不明"
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
        }
        for item in atom_items
    ]


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def normalize_link(link: str) -> str:
    parsed = urllib.parse.urlparse(link)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def classify(title: str, source: str = "") -> str:
    haystack = f"{title} {source}".lower()
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "其他":
            continue
        score = sum(1 for keyword in keywords if keyword_matches(haystack, keyword))
        if score:
            scores[category] = score
    if not scores:
        return "其他"
    return max(scores, key=lambda category: (scores[category], -list(CATEGORY_KEYWORDS).index(category)))


def keyword_matches(haystack: str, keyword: str) -> bool:
    keyword = keyword.lower().strip()
    if not keyword:
        return False
    if re.search(r"[\u4e00-\u9fff]", keyword):
        return keyword in haystack
    pattern = r"(?<![a-z0-9])" + re.escape(keyword).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def strip_source_suffix(title: str) -> str:
    return re.sub(r"\s+-\s+[^-]{2,80}$", "", title).strip()


def coverage_key(title: str) -> str:
    return normalize_title(strip_source_suffix(title))


def build_coverage_counts(raw_items: list[dict[str, str]]) -> dict[str, int]:
    sources_by_title: dict[str, set[str]] = {}
    for item in raw_items:
        title = item.get("title", "").strip()
        if not title:
            continue
        key = coverage_key(title)
        if not key:
            continue
        source = item.get("source", "").strip() or urllib.parse.urlparse(item.get("link", "")).netloc
        sources_by_title.setdefault(key, set()).add(source or "Unknown")
    return {key: len(sources) for key, sources in sources_by_title.items()}


def matched_important_keywords(item: NewsItem) -> dict[str, list[str]]:
    haystack = f"{item.title} {item.source}".lower()
    matches: dict[str, list[str]] = {}
    for group, keywords in IMPORTANT_KEYWORDS.items():
        group_matches = [keyword for keyword in keywords if keyword_matches(haystack, keyword)]
        if group_matches:
            matches[group] = group_matches
    return matches


def matched_headline_triggers(title: str) -> list[str]:
    haystack = title.lower()
    return [trigger for trigger in HEADLINE_TRIGGERS if headline_trigger_matches(haystack, trigger)]


def headline_trigger_matches(haystack: str, trigger: str) -> bool:
    trigger = trigger.lower().strip()
    if not trigger:
        return False
    suffixes = {
        "surge": r"(?:s|d|ing)?",
        "collapse": r"(?:s|d|ing)?",
        "warning": r"s?",
        "investigation": r"s?",
        "lawsuit": r"s?",
        "ban": r"(?:s|ned|ning)?",
        "restriction": r"s?",
        "launch": r"(?:es|ed|ing)?",
        "investment": r"s?",
        "record": r"s?",
    }
    suffix = suffixes.get(trigger, "")
    pattern = r"(?<![a-z0-9])" + re.escape(trigger) + suffix + r"(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def importance_score(item: NewsItem, coverage_counts: dict[str, int]) -> int:
    keyword_matches_count = sum(len(matches) for matches in matched_important_keywords(item).values())
    trigger_count = len(matched_headline_triggers(item.title))
    coverage_count = coverage_counts.get(coverage_key(item.title), 1)
    score = keyword_matches_count * 4
    score += trigger_count * 3
    score += min(max(coverage_count - 1, 0), 3) * 4
    if item.category != "其他":
        score += 2
    return score


def select_important_news(
    items: list[NewsItem],
    coverage_counts: dict[str, int],
    max_count: int = 20,
) -> list[NewsItem]:
    scored_items = [
        (importance_score(item, coverage_counts), item)
        for item in items
    ]
    scored_items = [(score, item) for score, item in scored_items if score > 0]

    def sort_key(scored_item: tuple[int, NewsItem]) -> tuple[int, int, str]:
        score, item = scored_item
        parsed = parse_date(item.published)
        timestamp = int(parsed.timestamp()) if parsed else 0
        return (score, timestamp, item.title)

    return [item for _, item in sorted(scored_items, key=sort_key, reverse=True)[:max_count]]


def extract_entities(item: NewsItem) -> list[str]:
    haystack = f"{item.title} {item.source}".lower()
    entities: list[str] = []
    for keyword, display_name in ENTITY_NAMES.items():
        if keyword_matches(haystack, keyword) and display_name not in entities:
            entities.append(display_name)
    return entities


def action_phrase(item: NewsItem) -> str:
    title = item.title.lower()
    checks = [
        (["record"], "創下新高或重要紀錄"),
        (["surge"], "出現明顯升勢"),
        (["collapse"], "出現急跌或重大挫折"),
        (["warning"], "發出風險警訊"),
        (["investigation"], "面臨調查"),
        (["lawsuit"], "捲入訴訟"),
        (["ban", "restriction"], "面臨禁令或限制"),
        (["launch"], "推出新產品或服務"),
        (["investment"], "擴大投資"),
        (["earnings"], "財報成為市場焦點"),
        (["ipo"], "IPO動向受到關注"),
        (["m&a", "acquisition"], "併購動向受到關注"),
        (["tariff", "trade"], "貿易政策風險升溫"),
    ]
    for keywords, phrase in checks:
        if any(headline_trigger_matches(title, keyword) for keyword in keywords):
            return phrase
    return {
        "AI": "AI競爭出現新動向",
        "半導體": "半導體供應鏈出現新動向",
        "美國科技股": "美國科技股走勢受到關注",
        "中國科技": "中國科技產業出現新動向",
        "宏觀經濟": "宏觀政策訊號受到關注",
        "金融市場": "金融市場波動受到關注",
    }.get(item.category, "新聞事件值得留意")


def chinese_title(item: NewsItem) -> str:
    entities = extract_entities(item)
    subject = "、".join(entities[:2]) if entities else item.category
    return f"{subject}：{action_phrase(item)}"


def truncate_text(value: str, max_chars: int = 50) -> str:
    value = re.sub(r"\s+", "", value.strip())
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip("，、；") + "…"


def chinese_summary(item: NewsItem) -> str:
    entities = extract_entities(item)
    subject = "、".join(entities[:2]) if entities else item.category
    templates = {
        "AI": f"{subject}相關消息顯示，AI投資與產品競爭持續升溫。",
        "半導體": f"{subject}動向牽動晶片供應鏈與AI運算需求。",
        "美國科技股": f"{subject}消息可能影響大型科技股與Nasdaq走勢。",
        "中國科技": f"{subject}動向反映中國科技競爭與監管變化。",
        "宏觀經濟": f"{subject}訊號可能影響利率預期與風險資產。",
        "金融市場": f"{subject}消息牽動股債匯與商品市場情緒。",
    }
    return truncate_text(templates.get(item.category, f"{subject}新聞值得列入今日觀察清單。"))


def why_important(item: NewsItem, coverage_counts: dict[str, int]) -> str:
    base = {
        "AI": "這則新聞有助判斷AI投資、產品化與企業採用速度。",
        "半導體": "這則新聞可能影響晶片供需、先進製程與AI伺服器供應鏈。",
        "美國科技股": "這則新聞會影響大型科技股估值與市場風險偏好。",
        "中國科技": "這則新聞有助追蹤中國科技公司、AI競爭與監管風向。",
        "宏觀經濟": "這則新聞可能改變利率、通膨或經濟成長預期。",
        "金融市場": "這則新聞可能牽動股市、債市、匯率或商品價格。",
    }.get(item.category, "這則新聞可能提供今日國際財經與科技議題線索。")

    coverage_count = coverage_counts.get(coverage_key(item.title), 1)
    if coverage_count > 1:
        return f"{base} 多家媒體同時報導，代表市場或產業關注度較高。"
    if matched_headline_triggers(item.title):
        return f"{base} 標題出現重大變化或風險訊號，值得優先查證。"
    return base


def possible_impacts(item: NewsItem) -> list[str]:
    impacts = extract_entities(item)
    by_category = {
        "AI": ["AI基礎設施", "企業AI應用", "雲端服務"],
        "半導體": ["晶片供應鏈", "AI伺服器供應鏈", "先進製程"],
        "美國科技股": ["美國科技股", "Nasdaq", "雲端與廣告市場"],
        "中國科技": ["中國科技股", "中美科技監管", "AI應用市場"],
        "宏觀經濟": ["美國公債", "美元", "風險資產"],
        "金融市場": ["股市", "債市", "外匯與商品市場"],
    }
    for impact in by_category.get(item.category, ["相關公司", "相關產業", "金融市場"]):
        if impact not in impacts:
            impacts.append(impact)
    return impacts[:6]


def follow_up_items(item: NewsItem) -> list[str]:
    items = {
        "AI": ["產品採用速度", "企業客戶名單", "資本支出指引"],
        "半導體": ["下一季財報", "出貨與庫存變化", "供應鏈產能調整"],
        "美國科技股": ["管理層評論", "財測與資本支出", "監管政策"],
        "中國科技": ["監管政策", "出口管制變化", "中國市場需求"],
        "宏觀經濟": ["央行官員談話", "通膨與就業數據", "利率路徑預期"],
        "金融市場": ["成交量與波動率", "資金流向", "美元與公債殖利率"],
    }.get(item.category, ["後續官方說法", "相關公司回應", "市場反應"])

    triggers = matched_headline_triggers(item.title)
    if "lawsuit" in triggers or "investigation" in triggers:
        items.append("法律或監管文件")
    if "launch" in triggers:
        items.append("產品上市時間表")
    if "investment" in triggers:
        items.append("投資金額與回收期")
    if "earnings" in matched_important_keywords(item).get("市場", []):
        items.append("下一季財報指引")

    result: list[str] = []
    for follow_up in items:
        if follow_up not in result:
            result.append(follow_up)
    return result[:5]


def render_ai_candidates(
    candidates: list[NewsItem],
    coverage_counts: dict[str, int],
    max_candidates: int,
) -> str:
    now = local_now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# 繁體中文記者研究分析",
        "",
        f"更新時間：{now}",
        "",
        f"入選新聞：{len(candidates)} / 最多 {max_candidates} 則",
        "",
        "說明：本檔案以本機規則篩選與改寫，不使用 OpenAI API；中文標題與摘要是研究提示，不是逐字翻譯。",
        "",
    ]

    if not candidates:
        lines.extend(["今日暫無符合條件的重要新聞。", ""])
        return "\n".join(lines)

    for index, item in enumerate(candidates, 1):
        lines.extend(
            [
                f"## {index}. {chinese_title(item)}",
                "",
                "原文標題：",
                item.title,
                "",
                "中文標題：",
                chinese_title(item),
                "",
                "中文摘要：",
                chinese_summary(item),
                "",
                "為什麼重要：",
                why_important(item, coverage_counts),
                "",
                "可能影響：",
            ]
        )
        lines.extend(f"- {impact}" for impact in possible_impacts(item))
        lines.extend(["", "建議追蹤："])
        lines.extend(f"- {follow_up}" for follow_up in follow_up_items(item))
        lines.extend(
            [
                "",
                f"來源：{item.source}",
                f"時間：{item.published}",
                f"連結：{item.link}",
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)


def deduplicate(raw_items: list[dict[str, str]]) -> list[NewsItem]:
    seen_titles: set[str] = set()
    seen_links: set[str] = set()
    items: list[NewsItem] = []
    for raw in raw_items:
        title = raw["title"].strip()
        link = raw["link"].strip()
        if not title or not link:
            continue
        title_key = coverage_key(title)
        link_key = normalize_link(link)
        if title_key in seen_titles or link_key in seen_links:
            continue
        seen_titles.add(title_key)
        seen_links.add(link_key)
        items.append(
            NewsItem(
                title=title,
                source=raw["source"] or urllib.parse.urlparse(link).netloc,
                published=raw["published"],
                link=link,
                category=classify(title, raw["source"]),
            )
        )
    return items


def sort_items(items: list[NewsItem]) -> list[NewsItem]:
    def sort_key(item: NewsItem) -> tuple[int, str]:
        parsed = parse_date(item.published)
        timestamp = int(parsed.timestamp()) if parsed else 0
        return (timestamp, item.title)

    return sorted(items, key=sort_key, reverse=True)


def most_common(values: list[str], limit: int) -> list[str]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return [
        value
        for value, _ in sorted(counts.items(), key=lambda pair: (pair[1], pair[0]), reverse=True)[:limit]
    ]


def trend_observations(items: list[NewsItem], candidates: list[NewsItem]) -> tuple[str, str, str]:
    focus_items = candidates or items[:20]
    tech_categories = {"AI", "半導體", "美國科技股", "中國科技"}
    finance_categories = {"宏觀經濟", "金融市場"}
    tech_items = [item for item in focus_items if item.category in tech_categories]
    finance_items = [item for item in focus_items if item.category in finance_categories]

    tech_topics = most_common([item.category for item in tech_items], 2)
    tech_entities = most_common(
        [entity for item in tech_items for entity in extract_entities(item)],
        3,
    )
    finance_topics = most_common([item.category for item in finance_items], 2)
    finance_entities = most_common(
        [entity for item in finance_items for entity in extract_entities(item)],
        3,
    )

    tech_subject = "、".join(tech_topics or ["AI", "半導體"])
    tech_names = "、".join(tech_entities)
    if tech_names:
        tech = f"{tech_subject}是今日科技主線，{tech_names}相關消息牽動算力、產品發布與供應鏈。"
    else:
        tech = f"{tech_subject}是今日科技主線，焦點落在算力需求、產品發布與供應鏈調整。"

    finance_subject = "、".join(finance_topics or ["宏觀經濟", "金融市場"])
    finance_names = "、".join(finance_entities)
    if finance_names:
        finance = f"{finance_subject}是今日財經主線，{finance_names}消息影響利率預期與風險偏好。"
    else:
        finance = f"{finance_subject}是今日財經主線，利率、通膨、財報與貿易政策牽動市場情緒。"

    follow_topics = most_common([item.category for item in focus_items if item.category != "其他"], 3)
    follow = f"未來一週留意：{'、'.join(follow_topics or ['AI', '半導體', '利率'])}，以及財報、監管政策與供應鏈變化。"

    return truncate_text(tech, 100), truncate_text(finance, 100), truncate_text(follow, 100)


def add_full_research_item(lines: list[str], item: NewsItem, coverage_counts: dict[str, int]) -> None:
    lines.extend(
        [
            "原文標題：",
            item.title,
            "",
            "中文標題：",
            chinese_title(item),
            "",
            "中文摘要：",
            chinese_summary(item),
            "",
            "為什麼重要：",
            why_important(item, coverage_counts),
            "",
            "可能影響：",
        ]
    )
    lines.extend(f"- {impact}" for impact in possible_impacts(item))
    lines.extend(["", "建議追蹤："])
    lines.extend(f"- {follow_up}" for follow_up in follow_up_items(item))
    lines.extend(["", "原文連結：", item.link, "", "---", ""])


def add_category_item(lines: list[str], item: NewsItem) -> None:
    lines.extend(
        [
            f"- 中文標題：{chinese_title(item)}",
            f"  - 中文摘要：{chinese_summary(item)}",
            f"  - 原文來源：{item.source}",
            f"  - 原文連結：{item.link}",
        ]
    )


def render_markdown(
    items: list[NewsItem],
    errors: list[str],
    max_per_category: int,
    top_items: list[NewsItem],
    coverage_counts: dict[str, int],
) -> str:
    today = local_now().strftime("%Y-%m-%d")
    lines = [
        f"# Daily Research Brief - {today}",
        "",
        "## 今日最值得追蹤（Top 10）",
        "",
    ]

    if not top_items:
        lines.extend(["今日暫無符合條件的重要新聞。", ""])
    else:
        for item in top_items[:10]:
            add_full_research_item(lines, item, coverage_counts)

    for category in CATEGORY_KEYWORDS:
        category_items = [item for item in items if item.category == category][:max_per_category]
        lines.append(f"## {category}")
        lines.append("")
        if not category_items:
            lines.append("- 今日暫無明顯相關新聞。")
        else:
            for item in category_items:
                add_category_item(lines, item)
        lines.append("")

    if errors:
        lines.extend(["## 抓取提醒", ""])
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")

    tech_trend, finance_trend, follow_trend = trend_observations(items, top_items)
    lines.extend([
        "# 今日趨勢觀察",
        "",
        "1. 今日最重要科技趨勢",
        tech_trend,
        "",
        "2. 今日最重要財經趨勢",
        finance_trend,
        "",
        "3. 值得未來一週追蹤的主題",
        follow_trend,
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取 RSS 新聞並產生 daily_brief.md")
    parser.add_argument("--feeds", type=Path, default=DEFAULT_FEEDS_FILE, help="RSS 清單檔案")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE, help="輸出 Markdown 檔案")
    parser.add_argument("--candidates-output", type=Path, default=DEFAULT_CANDIDATES_FILE, help="重要新聞研究分析輸出檔案")
    parser.add_argument("--max-per-category", type=int, default=12, help="每個分類最多輸出幾則")
    parser.add_argument("--max-candidates", type=int, default=20, help="重要新聞最多輸出幾則")
    args = parser.parse_args()

    if not args.feeds.exists():
        print(f"找不到 RSS 清單：{args.feeds}", file=sys.stderr)
        return 1

    feeds = read_feeds(args.feeds)
    raw_items: list[dict[str, str]] = []
    errors: list[str] = []

    for feed in feeds:
        try:
            raw_items.extend(parse_feed(fetch_xml(feed.url), feed))
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            errors.append(f"{feed.name} 抓取失敗：{exc}")

    coverage_counts = build_coverage_counts(raw_items)
    items = sort_items(deduplicate(raw_items))
    candidates = select_important_news(items, coverage_counts, args.max_candidates)
    args.output.write_text(
        render_markdown(items, errors, args.max_per_category, candidates[:10], coverage_counts),
        encoding="utf-8",
    )
    args.candidates_output.write_text(
        render_ai_candidates(candidates, coverage_counts, args.max_candidates),
        encoding="utf-8",
    )
    print(f"已輸出 {args.output}，共 {len(items)} 則新聞。")
    print(f"已輸出 {args.candidates_output}，共 {len(candidates)} 則重要新聞。")
    if errors:
        print(f"有 {len(errors)} 個來源抓取失敗，詳見輸出檔的「抓取提醒」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
