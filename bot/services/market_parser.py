from __future__ import annotations

import re
import time
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

_ZERO_WIDTH_CHARS = "\u200c\u200d\u200e\u200f\ufeff"
_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u0600-\u06ff]+", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class MarketAsset(StrEnum):
    BTC = "btc"
    ETH = "eth"
    TRX = "trx"
    USDT = "usdt"
    USD = "usd"
    TOMAN = "toman"
    STARS = "stars"


class MarketParseRejectReason(StrEnum):
    EMPTY = "empty"
    SENTENCE = "sentence"
    UNKNOWN_TOKEN = "unknown_token"
    MULTI_INTENT = "multi_intent"
    AMBIGUOUS_ALIAS = "ambiguous_alias"
    INVALID_AMOUNT = "invalid_amount"
    DUPLICATE_MESSAGE = "duplicate_message"
    EDITED_MESSAGE = "edited_message"
    HISTORICAL_MESSAGE = "historical_message"


class MarketIntentType(StrEnum):
    PRICE = "price"
    CONVERSION = "conversion"


@dataclass(frozen=True)
class MarketIntent:
    intent_type: MarketIntentType
    asset: MarketAsset
    quote: MarketAsset | None = None
    amount: Decimal | None = None


@dataclass(frozen=True)
class MarketParseResult:
    intent: MarketIntent | None
    reject_reason: MarketParseRejectReason | None = None

    @property
    def accepted(self) -> bool:
        return self.intent is not None


@dataclass(frozen=True)
class IncomingMarketMessage:
    chat_id: int
    message_id: int
    text: str | None
    is_edited: bool = False


@dataclass
class _SeenMessage:
    seen_at: float


ALIASES: dict[MarketAsset, tuple[str, ...]] = {
    MarketAsset.BTC: ("btc", "bitcoin", "بیتکوین", "بیت کوین", "بیت"),
    MarketAsset.ETH: ("eth", "ethereum", "اتر", "اتریوم"),
    MarketAsset.TRX: ("trx", "tron", "ترون"),
    MarketAsset.USDT: ("usdt", "tether", "تتر"),
    MarketAsset.USD: ("usd", "dollar", "دلار"),
    MarketAsset.TOMAN: ("toman", "irt", "تومان"),
    MarketAsset.STARS: ("stars", "star", "استار", "استارز", "ستاره"),
}

_ALIAS_LOOKUP: dict[tuple[str, ...], MarketAsset] = {}
for _asset, _aliases in ALIASES.items():
    for _alias in _aliases:
        _tokens = tuple(_TOKEN_RE.findall(_alias.casefold().translate(_PERSIAN_DIGITS)))
        if _tokens in _ALIAS_LOOKUP and _ALIAS_LOOKUP[_tokens] != _asset:
            raise RuntimeError(f"ambiguous market alias configured: {_alias}")
        _ALIAS_LOOKUP[_tokens] = _asset

_MAX_MARKET_TOKENS = 4
_QUOTE_ASSETS = {MarketAsset.USD, MarketAsset.USDT, MarketAsset.TOMAN}


def normalize_market_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold().translate(_PERSIAN_DIGITS)
    for char in _ZERO_WIDTH_CHARS:
        normalized = normalized.replace(char, " ")
    return " ".join(normalized.split())


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(normalize_market_text(text))


def _parse_amount(token: str) -> Decimal | None:
    if not _AMOUNT_RE.match(token):
        return None
    try:
        amount = Decimal(token)
    except InvalidOperation:
        return None
    return amount if amount > 0 else None


def _resolve_aliases(tokens: list[str]) -> tuple[list[MarketAsset], set[int], bool]:
    matches: list[tuple[int, int, MarketAsset]] = []
    ambiguous = False

    for start in range(len(tokens)):
        for end in range(len(tokens), start, -1):
            alias_tokens = tuple(tokens[start:end])
            asset = _ALIAS_LOOKUP.get(alias_tokens)
            if asset is not None:
                matches.append((start, end, asset))
                break

    occupied: set[int] = set()
    assets: list[MarketAsset] = []
    for start, end, asset in sorted(matches, key=lambda match: (match[0], -(match[1] - match[0]))):
        span = set(range(start, end))
        if occupied.intersection(span):
            ambiguous = True
            continue
        occupied.update(span)
        assets.append(asset)

    return assets, occupied, ambiguous


def parse_market_intent(text: str | None) -> MarketParseResult:
    if not text or not text.strip():
        return MarketParseResult(intent=None, reject_reason=MarketParseRejectReason.EMPTY)

    tokens = _tokenize(text)
    if not tokens:
        return MarketParseResult(intent=None, reject_reason=MarketParseRejectReason.EMPTY)
    if len(tokens) > _MAX_MARKET_TOKENS:
        return MarketParseResult(intent=None, reject_reason=MarketParseRejectReason.SENTENCE)

    aliases, alias_positions, ambiguous = _resolve_aliases(tokens)
    if ambiguous:
        return MarketParseResult(intent=None, reject_reason=MarketParseRejectReason.AMBIGUOUS_ALIAS)
    if not aliases:
        return MarketParseResult(intent=None, reject_reason=MarketParseRejectReason.UNKNOWN_TOKEN)
    if len(set(aliases)) != len(aliases):
        return MarketParseResult(intent=None, reject_reason=MarketParseRejectReason.MULTI_INTENT)

    amounts: list[Decimal] = []
    for index, token in enumerate(tokens):
        if index in alias_positions:
            continue
        amount = _parse_amount(token)
        if amount is None:
            return MarketParseResult(
                intent=None, reject_reason=MarketParseRejectReason.UNKNOWN_TOKEN
            )
        amounts.append(amount)

    if len(amounts) > 1:
        return MarketParseResult(intent=None, reject_reason=MarketParseRejectReason.INVALID_AMOUNT)

    if len(aliases) == 1 and not amounts:
        return MarketParseResult(
            intent=MarketIntent(intent_type=MarketIntentType.PRICE, asset=aliases[0])
        )

    if len(aliases) == 1 and amounts:
        return MarketParseResult(
            intent=MarketIntent(
                intent_type=MarketIntentType.CONVERSION,
                asset=aliases[0],
                amount=amounts[0],
            )
        )

    if len(aliases) == 2 and amounts:
        source, quote = aliases
        if source in _QUOTE_ASSETS and quote not in _QUOTE_ASSETS:
            source, quote = quote, source
        if source == quote or quote not in _QUOTE_ASSETS:
            return MarketParseResult(
                intent=None, reject_reason=MarketParseRejectReason.MULTI_INTENT
            )
        return MarketParseResult(
            intent=MarketIntent(
                intent_type=MarketIntentType.CONVERSION,
                asset=source,
                quote=quote,
                amount=amounts[0],
            )
        )

    return MarketParseResult(intent=None, reject_reason=MarketParseRejectReason.MULTI_INTENT)


class MarketMessageIdempotencyGuard:
    def __init__(self, *, ttl_seconds: int = 20 * 60, max_entries: int = 10_000) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._seen: OrderedDict[tuple[int, int], _SeenMessage] = OrderedDict()
        self._highest_message_id_by_chat: dict[int, int] = {}

    def check(
        self, message: IncomingMarketMessage, *, allow_edited: bool = False
    ) -> MarketParseResult:
        if message.is_edited and not allow_edited:
            return MarketParseResult(
                intent=None, reject_reason=MarketParseRejectReason.EDITED_MESSAGE
            )

        now = time.monotonic()
        self._prune(now)
        key = (message.chat_id, message.message_id)
        if key in self._seen:
            return MarketParseResult(
                intent=None, reject_reason=MarketParseRejectReason.DUPLICATE_MESSAGE
            )

        highest = self._highest_message_id_by_chat.get(message.chat_id)
        if highest is not None and message.message_id <= highest:
            return MarketParseResult(
                intent=None, reject_reason=MarketParseRejectReason.HISTORICAL_MESSAGE
            )

        self._seen[key] = _SeenMessage(seen_at=now)
        self._highest_message_id_by_chat[message.chat_id] = message.message_id
        return parse_market_intent(message.text)

    def _prune(self, now: float) -> None:
        expires_before = now - self._ttl_seconds
        while self._seen:
            _, seen = next(iter(self._seen.items()))
            if seen.seen_at > expires_before and len(self._seen) <= self._max_entries:
                break
            self._seen.popitem(last=False)
