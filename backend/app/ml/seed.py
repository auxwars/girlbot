"""A handful of illustrative labeled examples so the app isn't a blank slate on
first run. These are generic (NOT your girlfriend) and flagged is_seed=1, so you
can wipe them all with one button on the Training page once you've added real
data. Replacing them with your own labeled texts is the whole point.
"""
from .. import db

SEED_EXAMPLES = [
    ("I'm fine.", "after I cancelled plans to hang with the boys",
     "She is NOT fine. She's hurt I ditched her and wants me to notice and make it right.",
     "annoyed_indirect"),
    ("do whatever you want", "when I asked if she minded me gaming tonight",
     "This is a trap answer. She minds. She wants me to choose her.",
     "annoyed_indirect"),
    ("k", "mid-conversation, out of nowhere",
     "Something I said landed wrong. Short + dry = she's annoyed.",
     "annoyed_indirect"),
    ("i miss youuu", "random afternoon text",
     "Genuine affection, wants attention back. Easy — just match her energy.",
     "affection"),
    ("look at this dog omg", "sent me a photo",
     "A bid for connection. She wants me to react and share the moment, not just leave her on read.",
     "bid_connection"),
    ("what time are we meeting tmr", "planning a date",
     "Literally just logistics. No subtext, answer the question.",
     "logistics"),
    ("do you even still like me", "late at night after a quiet day",
     "She's feeling insecure and wants reassurance, not a debate.",
     "wants_reassurance"),
    ("i just need some time to myself tonight", "after a stressful week",
     "She genuinely wants space. Don't take it personal, give her room.",
     "wants_space"),
    ("we should totally get food sometime", "dropped casually twice this week",
     "She's hinting she wants me to actually plan a date, not say 'yeah sometime'.",
     "hint_action"),
    ("i'm so happy right now :)", "after a good day together",
     "Genuinely happy, means exactly what she says.",
     "happy_genuine"),
    ("guess you were busy huh", "after I took a while to reply",
     "Testing whether I'll notice and reassure her that she's a priority.",
     "testing"),
    ("nothing's wrong", "with a sigh, arms crossed",
     "Something is very much wrong. Classic indirect. She wants me to gently pull it out of her.",
     "annoyed_indirect"),
]


def ensure_seed() -> None:
    """Insert seed rows only if the examples table is completely empty."""
    if db.count_examples() > 0:
        return
    for her, ctx, meaning, intent in SEED_EXAMPLES:
        db.add_example(her, ctx, meaning, intent, is_seed=1)
