"""The set of 'meanings' the model learns to sort her messages into.

Grounded in a few well-known relationship-communication ideas: indirect
communication ("I'm fine" rarely means fine), Gottman's 'bids for connection',
and the difference between literal logistics and loaded hints.

These are the DEFAULT labels. You can use whatever intent strings you want when
adding examples on the training page — the model just learns from whatever
labels appear in your data. These are here to give you a sane starting set and
to seed a cold-start demo.
"""

INTENTS: dict[str, str] = {
    "happy_genuine": "Actually happy / content. Means what she says, no subtext.",
    "annoyed_indirect": "Upset or irritated but downplaying it ('I'm fine', 'do whatever').",
    "wants_reassurance": "Feeling insecure; wants you to reassure or affirm her.",
    "wants_space": "Needs alone time or to cool off; not a test, genuinely wants room.",
    "testing": "Testing your attention/effort to see if you'll notice or push back.",
    "hint_action": "Dropping a hint that she wants you to DO something specific.",
    "bid_connection": "Reaching for your attention/closeness (a 'bid'). Wants you to turn toward her.",
    "logistics": "Literal plans or info. No hidden meaning — take it at face value.",
    "affection": "Expressing warmth, flirting, or love.",
}

INTENT_KEYS = list(INTENTS.keys())
