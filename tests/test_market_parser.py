from decimal import Decimal

from bot.services.market_parser import (
    IncomingMarketMessage,
    MarketAsset,
    MarketIntentType,
    MarketMessageIdempotencyGuard,
    MarketParseRejectReason,
    parse_market_intent,
)


def test_single_asset_request_resolves_to_one_intent() -> None:
    result = parse_market_intent("btc")

    assert result.accepted
    assert result.intent is not None
    assert result.intent.intent_type == MarketIntentType.PRICE
    assert result.intent.asset == MarketAsset.BTC


def test_persian_conversion_request_is_strict() -> None:
    result = parse_market_intent("۱ ترون تومان")

    assert result.accepted
    assert result.intent is not None
    assert result.intent.asset == MarketAsset.TRX
    assert result.intent.quote == MarketAsset.TOMAN
    assert result.intent.amount == Decimal("1")


def test_quote_first_conversion_is_normalized_to_asset_first() -> None:
    result = parse_market_intent("100 usd trx")

    assert result.accepted
    assert result.intent is not None
    assert result.intent.asset == MarketAsset.TRX
    assert result.intent.quote == MarketAsset.USD
    assert result.intent.amount == Decimal("100")


def test_keyword_inside_sentence_is_rejected() -> None:
    result = parse_market_intent("من امروز بیت خریدم")

    assert not result.accepted
    assert result.reject_reason == MarketParseRejectReason.UNKNOWN_TOKEN


def test_long_sentence_with_alias_is_rejected_before_conversion() -> None:
    result = parse_market_intent("today I bought btc and want to hold it")

    assert not result.accepted
    assert result.reject_reason == MarketParseRejectReason.SENTENCE


def test_overlapping_duplicate_aliases_do_not_create_multiple_intents() -> None:
    result = parse_market_intent("bitcoin btc")

    assert not result.accepted
    assert result.reject_reason == MarketParseRejectReason.MULTI_INTENT


def test_edited_message_is_blocked_by_default() -> None:
    guard = MarketMessageIdempotencyGuard()
    result = guard.check(IncomingMarketMessage(1, 10, "btc", is_edited=True))

    assert not result.accepted
    assert result.reject_reason == MarketParseRejectReason.EDITED_MESSAGE


def test_duplicate_message_id_is_idempotently_blocked() -> None:
    guard = MarketMessageIdempotencyGuard()

    first = guard.check(IncomingMarketMessage(1, 10, "btc"))
    duplicate = guard.check(IncomingMarketMessage(1, 10, "trx"))

    assert first.accepted
    assert not duplicate.accepted
    assert duplicate.reject_reason == MarketParseRejectReason.DUPLICATE_MESSAGE


def test_historical_message_id_is_blocked_after_newer_message() -> None:
    guard = MarketMessageIdempotencyGuard()

    first = guard.check(IncomingMarketMessage(1, 10, "btc"))
    historical = guard.check(IncomingMarketMessage(1, 9, "trx"))

    assert first.accepted
    assert not historical.accepted
    assert historical.reject_reason == MarketParseRejectReason.HISTORICAL_MESSAGE
