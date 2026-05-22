"""Intent patterns contributed by the ecommerce module.

Each pattern is matched purely by keyword presence (case-insensitive)
against the user query. Patterns are intentionally narrow and the
keyword list is hand-curated to bias toward precision — false
positives are far more harmful than false negatives here, because the
main chat UI gates this whole router path behind an explicit
"Ecommerce mode" toggle (see `web/components/chat/chat-shell.tsx`),
and a missed intent inside that toggle simply means the user's
question is forwarded to the default chat path unchanged.

The keyword lists are split per intent so the matcher attributes a
hit to the most specific intent (highest `weight`) when the same
query overlaps multiple patterns — e.g. "compare iphone 15 vs pixel
9" matches both ``ecommerce.product_compare`` and
``ecommerce.product_consult`` but the compare intent's higher weight
wins.

All three patterns map to the same downstream lane today
(``run_ecommerce_chat_stream``), but the per-intent split keeps the
door open for future routing variants — e.g. ``product_compare`` may
later prefer the `/internal/ecommerce/compare` lane instead of the
LLM stream.
"""

from __future__ import annotations

from ragent_python.core.router.intent import IntentPattern


ECOMMERCE_INTENT_PRODUCT_CONSULT = "ecommerce.product_consult"
ECOMMERCE_INTENT_PRODUCT_COMPARE = "ecommerce.product_compare"
ECOMMERCE_INTENT_PRODUCT_BUY = "ecommerce.product_buy"


_PRODUCT_NOUN_KEYWORDS: tuple[str, ...] = (
    "laptop", "laptops",
    "notebook",
    "macbook",
    "thinkpad",
    "ultrabook",
    "phone", "phones",
    "smartphone", "smartphones",
    "iphone",
    "android",
    "pixel",
    "tablet", "tablets",
    "ipad",
    "monitor", "monitors",
    "display ",
    "earbuds",
    "headphone", "headphones",
    "airpods",
    "headset",
)


_BUY_VERB_KEYWORDS: tuple[str, ...] = (
    "buy",
    "purchase",
    "order ",
    "checkout",
    "add to cart",
    "shop for",
    "shopping for",
    "looking to buy",
    "ready to buy",
)


_RECOMMEND_VERB_KEYWORDS: tuple[str, ...] = (
    "recommend",
    "recommendation",
    "recommendations",
    "suggest a ",
    "suggest some ",
    "which should i buy",
    "what should i buy",
    "help me pick",
    "help me choose",
    "best ",
    "好的 ",
    "推荐",
    "买什么",
)


_COMPARE_VERB_KEYWORDS: tuple[str, ...] = (
    "compare ",
    "vs ",
    " vs.",
    "versus",
    "spec compare",
    "side by side",
    "difference between",
    "which is better",
    "对比",
)


def _ecommerce_product_consult_pattern() -> IntentPattern:
    return IntentPattern(
        name=ECOMMERCE_INTENT_PRODUCT_CONSULT,
        module="ecommerce",
        keywords=tuple(
            sorted(set(_PRODUCT_NOUN_KEYWORDS + _RECOMMEND_VERB_KEYWORDS))
        ),
        description=(
            "Catalog browse / recommendation intent: user mentions a "
            "category noun (laptop, phone, tablet, monitor, earbuds, …) "
            "or asks for a recommendation."
        ),
        weight=1.0,
        tags=("ecommerce", "consult"),
    )


def _ecommerce_product_compare_pattern() -> IntentPattern:
    return IntentPattern(
        name=ECOMMERCE_INTENT_PRODUCT_COMPARE,
        module="ecommerce",
        keywords=tuple(sorted(set(_COMPARE_VERB_KEYWORDS))),
        description=(
            "Explicit comparison intent: 'compare X vs Y', 'difference "
            "between …', '… which is better?'."
        ),
        weight=2.0,
        tags=("ecommerce", "compare"),
    )


def _ecommerce_product_buy_pattern() -> IntentPattern:
    return IntentPattern(
        name=ECOMMERCE_INTENT_PRODUCT_BUY,
        module="ecommerce",
        keywords=tuple(sorted(set(_BUY_VERB_KEYWORDS))),
        description=(
            "Purchase-intent verbs (buy / purchase / order). Highest "
            "weight because the verb itself is rarely ambiguous."
        ),
        weight=3.0,
        tags=("ecommerce", "buy"),
    )


def build_ecommerce_intent_patterns() -> tuple[IntentPattern, ...]:
    return (
        _ecommerce_product_consult_pattern(),
        _ecommerce_product_compare_pattern(),
        _ecommerce_product_buy_pattern(),
    )
