"""Rule-based natural language understanding for the finance assistant.

Pipeline: normalize -> resolve date range -> extract entities -> detect intent.
Deterministic and local: no external language model is used, and the parsed
result can only select from a fixed set of intents handled by trusted code.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.dates import MONTH_NAMES, add_months, format_date

MAX_QUERY_LENGTH = 500

CATEGORY_SYNONYMS: dict[str, list[str]] = {
    "food": ["food", "dining", "restaurant", "restaurants", "eating out", "eat out", "takeout", "take out",
             "food delivery", "delivery", "swiggy", "zomato", "cafe", "coffee", "lunch", "dinner", "breakfast", "snacks"],
    "groceries": ["grocery", "groceries", "supermarket", "vegetables", "kirana"],
    "transportation": ["transport", "transportation", "travel to work", "commute", "cab", "cabs", "taxi", "uber",
                       "ola", "fuel", "petrol", "diesel", "metro", "bus", "auto"],
    "education": ["education", "books", "course", "courses", "tuition", "college fees", "school", "fees"],
    "healthcare": ["health", "healthcare", "medical", "medicine", "medicines", "doctor", "pharmacy", "hospital"],
    "housing": ["housing", "rent", "home", "house", "maintenance"],
    "utilities": ["utilities", "utility", "electricity", "power bill", "water bill", "internet", "broadband",
                  "phone bill", "mobile bill", "recharge", "gas bill"],
    "shopping": ["shopping", "clothes", "clothing", "amazon", "flipkart", "myntra", "electronics", "gadgets"],
    "entertainment": ["entertainment", "movies", "movie", "cinema", "games", "gaming", "concert", "fun"],
    "travel": ["travel", "trip", "trips", "vacation", "holiday", "flights", "flight", "hotel", "hotels", "train"],
    "subscriptions": ["subscription", "subscriptions", "netflix", "spotify", "prime", "ott", "streaming", "membership"],
    "other": ["other", "miscellaneous", "misc"],
}

VAGUE_TIME = re.compile(r"\b(recently|lately|a while ago|the other day|some time ago|earlier)\b")


@dataclass
class Period:
    start: dt.date
    end: dt.date
    label: str
    explicit: bool = True

    def as_dict(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "label": self.label}


@dataclass
class ParsedQuery:
    text: str
    intent: str
    period: Period | None = None
    vague_time: bool = False
    categories: list[str] = field(default_factory=list)
    merchant: str | None = None
    percent: Decimal | None = None
    amount: Decimal | None = None
    goal_hint: str | None = None
    limit: int | None = None


def normalize(text: str) -> str:
    text = text.strip().lower()[:MAX_QUERY_LENGTH]
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[?!]+", " ", text)
    text = re.sub(r"[^\w\s₹$%.,/'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------- dates ----------------

MONTH_RE = "|".join(sorted(MONTH_NAMES + [m[:3] for m in MONTH_NAMES] + ["sept"], key=len, reverse=True))


def _month_number(token: str) -> int:
    token = token.lower()
    for i, name in enumerate(MONTH_NAMES):
        if token == name or token == name[:3] or (token == "sept" and i == 8):
            return i + 1
    raise ValueError(token)


def _parse_date_token(token: str, today: dt.date) -> dt.date | None:
    token = token.strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", token)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", token)
    if m:
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.fullmatch(rf"(\d{{1,2}})(?:st|nd|rd|th)? ({MONTH_RE})(?: (\d{{4}}))?", token)
    if m:
        year = int(m.group(3)) if m.group(3) else today.year
        return dt.date(year, _month_number(m.group(2)), int(m.group(1)))
    m = re.fullmatch(rf"({MONTH_RE}) (\d{{1,2}})(?:st|nd|rd|th)?(?:,? (\d{{4}}))?", token)
    if m:
        year = int(m.group(3)) if m.group(3) else today.year
        return dt.date(year, _month_number(m.group(1)), int(m.group(2)))
    return None


DATE_TOKEN = rf"(\d{{4}}-\d{{1,2}}-\d{{1,2}}|\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{4}}|\d{{1,2}}(?:st|nd|rd|th)? (?:{MONTH_RE})(?: \d{{4}})?|(?:{MONTH_RE}) \d{{1,2}}(?:st|nd|rd|th)?(?:,? \d{{4}})?)"


def _month_period(year: int, month: int, today: dt.date) -> Period:
    start = dt.date(year, month, 1)
    end = dt.date(year, month, calendar.monthrange(year, month)[1])
    label = f"{calendar.month_name[month]} {year}"
    if start <= today <= end:
        end = today
        label += " (so far)"
    return Period(start, end, label)


def resolve_period(text: str, today: dt.date) -> Period | None:
    """Resolve the first recognizable date expression. Returns None if none found."""
    try:
        m = re.search(rf"\b(?:between|from) {DATE_TOKEN} (?:and|to|until|till) {DATE_TOKEN}", text)
        if m:
            a, b = _parse_date_token(m.group(1), today), _parse_date_token(m.group(2), today)
            if a and b:
                a, b = min(a, b), max(a, b)
                return Period(a, b, f"{format_date(a)} to {format_date(b)}")
        m = re.search(rf"\bsince {DATE_TOKEN}", text)
        if m and (a := _parse_date_token(m.group(1), today)):
            return Period(a, today, f"since {format_date(a)}")
        m = re.search(rf"\bsince ({MONTH_RE})(?: (\d{{4}}))?\b", text)
        if m:
            month = _month_number(m.group(1))
            year = int(m.group(2)) if m.group(2) else (today.year if month <= today.month else today.year - 1)
            start = dt.date(year, month, 1)
            return Period(start, today, f"since {calendar.month_name[month]} {year}")
        m = re.search(rf"\bon {DATE_TOKEN}", text)
        if m and (a := _parse_date_token(m.group(1), today)):
            return Period(a, a, format_date(a))
    except ValueError:
        return None

    if re.search(r"\btoday\b", text):
        return Period(today, today, "today")
    if re.search(r"\byesterday\b", text):
        y = today - dt.timedelta(days=1)
        return Period(y, y, "yesterday")
    if re.search(r"\b(this|current) week\b", text):
        start = today - dt.timedelta(days=today.weekday())
        return Period(start, today, "this week")
    if re.search(r"\b(last|previous|past) week\b", text):
        end = today - dt.timedelta(days=today.weekday() + 1)
        return Period(end - dt.timedelta(days=6), end, "last week")
    m = re.search(r"\b(?:last|past|previous) (\d{1,3}) days?\b", text)
    if m:
        n = max(1, min(int(m.group(1)), 1095))
        return Period(today - dt.timedelta(days=n - 1), today, f"the last {n} days")
    m = re.search(r"\b(?:last|past|previous) (\d{1,2}) months?\b", text)
    if m:
        n = max(1, min(int(m.group(1)), 36))
        start = add_months(today, -n) + dt.timedelta(days=1)
        return Period(start, today, f"the last {n} months")
    if re.search(r"\b(this|current) month\b|\bso far\b|\bmonth to date\b", text):
        return _month_period(today.year, today.month, today)
    if re.search(r"\b(last|previous|past) month\b", text):
        prev = add_months(today.replace(day=1), -1)
        return _month_period(prev.year, prev.month, today)
    if re.search(r"\b(this|current) year\b|\byear to date\b", text):
        return Period(dt.date(today.year, 1, 1), today, f"{today.year} (so far)")
    if re.search(r"\b(last|previous) year\b", text):
        y = today.year - 1
        return Period(dt.date(y, 1, 1), dt.date(y, 12, 31), str(y))
    for m in re.finditer(rf"\b(?:(in|during|for|of) )?({MONTH_RE})(?: (\d{{4}}))?\b", text):
        # "may" is usually a verb ("may I ..."); only treat it as a month with context.
        if m.group(2) == "may" and not (m.group(1) or m.group(3)):
            continue
        month = _month_number(m.group(2))
        if m.group(3):
            year = int(m.group(3))
        else:
            # A month name without a year means the most recent such month.
            year = today.year if month <= today.month else today.year - 1
        return _month_period(year, month, today)
    return None


# ---------------- entities ----------------

def extract_categories(text: str, category_names: dict[str, str]) -> list[str]:
    found: list[tuple[int, str]] = []
    for cat_id, name in category_names.items():
        terms = set(CATEGORY_SYNONYMS.get(cat_id, [])) | {name.lower(), cat_id.replace("_", " ")}
        if "&" in name:
            terms |= {part.strip().lower() for part in name.split("&")}
        for term in terms:
            if term and (m := re.search(rf"\b{re.escape(term)}\b", text)):
                found.append((m.start(), cat_id))
                break
    found.sort()
    result = []
    for _, cat in found:
        if cat not in result:
            result.append(cat)
    return result


def extract_merchant(text: str, merchants: list[str]) -> str | None:
    best = None
    for merchant in merchants:
        norm = re.sub(r"[^a-z0-9 ]+", " ", merchant.lower()).strip()
        if len(norm) >= 3 and re.search(rf"\b{re.escape(norm)}\b", text):
            if best is None or len(norm) > len(best[1]):
                best = (merchant, norm)
    return best[0] if best else None


def extract_percent(text: str) -> Decimal | None:
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent|per cent)", text)
    return Decimal(m.group(1)) if m else None


def extract_amount(text: str) -> Decimal | None:
    m = re.search(r"(?:₹|rs\.?|inr|\$)\s*(\d[\d,]*(?:\.\d{1,2})?)|(\d[\d,]*(?:\.\d{1,2})?)\s*(?:rupees|rs\b|inr\b)", text)
    if not m:
        m = re.search(r"\bby (\d[\d,]*(?:\.\d{1,2})?)\b(?!\s*(?:%|percent|per cent))", text)
    if not m:
        return None
    raw = next(g for g in m.groups() if g)
    try:
        return Decimal(raw.replace(",", ""))
    except Exception:  # noqa: BLE001
        return None


# ---------------- intents ----------------

INTENT_RULES: list[tuple[str, re.Pattern]] = [
    ("help", re.compile(r"^(help|hi|hello|hey)$|\bwhat can (you|i) (do|ask)\b|\bwhat (questions|kind)\b|\bexamples?\b")),
    ("goal_requirement", re.compile(
        r"\b(goal|goals)\b.*\b(save|saving|need|reach|contribut)|\b(save|saving|need)\b.*\b(goal|goals)\b|"
        r"\bhow much .*\bsave (each|per|every|a) month\b")),
    ("simulate_saving", re.compile(
        r"\b(could|would|can|will) i save\b|\bsave by (reducing|cutting|spending less)\b|\bif i (reduce|cut|spend less|lower)\b|"
        r"\b(reduce|cut|cutting|reducing|lower)\b.*\bby\b")),
    ("category_change", re.compile(
        r"\b(which|what) categor(y|ies)\b.*\b(increase|increased|grew|rose|went up|jump|decrease|decreased|dropped|fell|went down|change|changed)\b|"
        r"\b(increase|increased|decrease|decreased)\b.*\bthe most\b")),
    ("budget_remaining", re.compile(
        r"\b(remaining|left)\b.*\bbudget\b|\bbudget\b.*\b(remaining|left)\b|\bhow much (can|do) i (still )?(spend|have)\b")),
    ("budget_status", re.compile(
        r"\b(approaching|near|close to|over|exceed|exceeded|exceeding|within|under|on track)\b.*\b(budget|limit)\b|"
        r"\bbudget (status|utili[sz]ation)\b|\bhow (am i|is my) .*budget\b")),
    ("unusual_transactions", re.compile(r"\b(unusual|unusually|anomal\w*|suspicious|odd|strange|abnormal|flagged)\b")),
    ("largest_transactions", re.compile(r"\b(largest|biggest|highest|most expensive|top \d+|top) (transactions?|expenses?|purchases?|payments?)\b|\blarge (transactions?|expenses?)\b")),
    ("top_category", re.compile(
        r"\b(which|what) categor(y|ies)\b.*\b(most|highest|biggest|largest|top)\b|\bwhere (did|do) i spend (the )?most\b|"
        r"\btop categor|\bbreakdown\b|\bspending by category\b|\bcategory wise\b")),
    ("list_transactions", re.compile(
        r"\b(list|show|which|what)\b.*\b(transactions|expenses|purchases|payments)\b|\bwhat did i (buy|pay for)\b|\brecorded\b")),
    ("average_spending", re.compile(r"\b(average|avg|per day|daily|typical)\b")),
    ("transaction_count", re.compile(r"\bhow many (transactions|expenses|purchases|times)\b")),
    ("total_spent", re.compile(
        r"\bhow much\b.*\b(spend|spent|spending|pay|paid|cost)\b|\btotal (spend|spent|spending|expenses?)\b|"
        r"\bwhat did i spend\b|\bmy (spending|expenses)\b|\bspent\b")),
    ("unsupported_income", re.compile(r"\b(income|salary|earn|earned|earning|invest|investment|stocks?|mutual funds?|loan|credit score|tax return)\b")),
]


def detect_intent(text: str) -> str:
    for intent, pattern in INTENT_RULES:
        if pattern.search(text):
            if intent == "unsupported_income":
                return "unsupported"
            return intent
    return "unsupported"


def parse_query(raw: str, today: dt.date, category_names: dict[str, str], merchants: list[str],
                goal_names: list[str]) -> ParsedQuery:
    text = normalize(raw)
    intent = detect_intent(text)
    # Income-related words override, since the app tracks expenses only.
    if re.search(r"\b(income|salary|earned|earnings)\b", text):
        intent = "unsupported"
    parsed = ParsedQuery(text=text, intent=intent)
    parsed.period = resolve_period(text, today)
    parsed.vague_time = bool(VAGUE_TIME.search(text)) and parsed.period is None
    parsed.categories = extract_categories(text, category_names)
    parsed.merchant = extract_merchant(text, merchants)
    parsed.percent = extract_percent(text)
    parsed.amount = None if parsed.percent is not None else extract_amount(text)
    m = re.search(r"\btop (\d{1,2})\b", text)
    parsed.limit = int(m.group(1)) if m else None
    for name in sorted(goal_names, key=len, reverse=True):
        norm = re.sub(r"[^a-z0-9 ]+", " ", name.lower()).strip()
        if norm and (re.search(rf"\b{re.escape(norm)}\b", text) or
                     any(len(w) >= 4 and re.search(rf"\b{re.escape(w)}\b", text) for w in norm.split())):
            parsed.goal_hint = name
            break
    return parsed
