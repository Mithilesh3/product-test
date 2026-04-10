from typing import Any, Dict


LIFE_PATH_ARCHETYPES = {
    1: {
        "title": "Strategic Leader",
        "description": "Independent, pioneering और leadership की तरफ naturally inclined ऊर्जा। यह archetype अपना रास्ता खुद बनाने और आसपास के systems पर असर डालने की मजबूत drive रखता है।",
    },
    2: {
        "title": "Empathic Advisor",
        "description": "Diplomatic, emotionally intelligent और relationship-oriented profile। यह archetype harmony, mediation और subtle influence के माध्यम से value create करता है।",
    },
    3: {
        "title": "Creative Communicator",
        "description": "Expressive, imaginative और socially magnetic pattern। ऐसे लोग ideas, communication और storytelling के through दुनिया पर असर डालते हैं।",
    },
    4: {
        "title": "Strategic Builder",
        "description": "Disciplined, practical और system-oriented ऊर्जा। यह archetype stable foundations, structure और reliable execution में सबसे ज्यादा चमकता है।",
    },
    5: {
        "title": "Adaptive Explorer",
        "description": "Dynamic, curious और freedom-seeking profile। ऐसे लोग नए experiences, learning cycles और fast adaptation के through evolve करते हैं।",
    },
    6: {
        "title": "Responsible Guardian",
        "description": "Supportive, caring और protective archetype। यह profile family, community और relationship systems में stabilizing force बन सकती है।",
    },
    7: {
        "title": "Analytical Seeker",
        "description": "Deep thinker, researcher और hidden patterns को observe करने वाला archetype। ऐसे लोग knowledge, philosophy और technical mastery की तरफ naturally जाते हैं।",
    },
    8: {
        "title": "Power Architect",
        "description": "Strategic, ambitious और achievement-focused energy। यह archetype governance, scale और material execution की दुनिया में strong परिणाम ला सकता है।",
    },
    9: {
        "title": "Humanitarian Visionary",
        "description": "Idealistic, compassionate और globally minded profile। ऐसे लोग meaningful impact, service और larger-purpose initiatives की तरफ strong pull महसूस करते हैं।",
    },
}

DESTINY_MODIFIERS = {
    1: "Independent",
    2: "Diplomatic",
    3: "Creative",
    4: "Structured",
    5: "Dynamic",
    6: "Responsible",
    7: "Analytical",
    8: "Ambitious",
    9: "Visionary",
}


def derive_behavior_modifier(scores: Dict[str, Any]) -> str:
    if not scores:
        return "Balanced Thinker"

    emotional = scores.get("emotional_regulation_index", 50)
    financial = scores.get("financial_discipline_index", 50)
    stability = scores.get("life_stability_index", 50)

    if emotional > 75 and stability > 70:
        return "Stable Strategist"
    if financial > 70:
        return "Resource Optimizer"
    if emotional < 40:
        return "Emotionally Reactive"
    return "Adaptive Thinker"


def generate_numerology_archetype(
    numerology_core: Dict[str, Any],
    scores: Dict[str, Any],
) -> Dict[str, Any]:
    pyth = numerology_core.get("pythagorean", {})
    life_path = pyth.get("life_path_number", 0)
    destiny = pyth.get("destiny_number", 0)

    base = LIFE_PATH_ARCHETYPES.get(life_path)
    if not base:
        return {}

    destiny_modifier = DESTINY_MODIFIERS.get(destiny, "Strategic")
    behavior_modifier = derive_behavior_modifier(scores)
    archetype_title = f"{destiny_modifier} {base['title']}"

    return {
        "archetype_name": archetype_title,
        "core_archetype": base["title"],
        "behavior_style": behavior_modifier,
        "description": base["description"],
        "interpretation": (
            f"यह profile {base['title']} की strategic traits को {destiny_modifier.lower()} expression style के साथ combine करती है। "
            f"Behavioral indicators यह दिखाते हैं कि decision making और life strategy में '{behavior_modifier}' pattern सक्रिय है।"
        ),
    }
