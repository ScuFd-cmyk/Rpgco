"""Static, data-driven game definitions. Adding a class, location or item
should mean editing data here, not rewriting services."""
from __future__ import annotations

CLASSES = {
    "sentinel": {"name": "Sentinel", "role": "Battlefield control and defense",
                 "signature": "Aegis Formation"},
    "arcanist": {"name": "Arcanist", "role": "Magic, utility and battlefield manipulation",
                 "signature": "Resonance Field"},
    "ranger":   {"name": "Ranger", "role": "Precision, reconnaissance and exploiting weakness",
                 "signature": "Exploit Weakness"},
}

ITEMS = {
    "whisperleaf":  {"name": "Whisperleaf", "description": "A silver-veined herb that hums faintly."},
    "bastion_iron": {"name": "Bastion Iron", "description": "Dark ore chipped from the Hollow Bastion."},
}

STARTING_LOCATION = "ashenhold"

# `requires` gates access on shared world state: (world key, minimum value).
LOCATIONS = {
    "ashenhold": {
        "name": "Ashenhold", "kind": "settlement",
        "description": "A walled refuge of soot and lantern-light. Its defenses can be reinforced.",
        "gather": None, "requires": None, "can_fortify": True,
    },
    "whispering_wilds": {
        "name": "Whispering Wilds", "kind": "wilderness",
        "description": "Mist-choked woods where the trees seem to murmur.",
        "gather": "whisperleaf", "requires": None, "can_fortify": False,
    },
    "hollow_bastion": {
        "name": "The Hollow Bastion", "kind": "stronghold",
        "description": "A ruined fortress. The approach is only safe once Ashenhold is well defended.",
        "gather": "bastion_iron", "requires": ("ashenhold_defense", 50), "can_fortify": False,
    },
}

FORTIFY_AMOUNT = 5
DEFENSE_MAX = 100
