from typing import Any, Dict, Optional


NUMBER_MANTRAS = {
    1: {
        "deity": "Surya (Sun)",
        "mantra_sanskrit": "ॐ घृणि सूर्याय नमः",
        "mantra_english": "Om Ghrini Suryaya Namaha",
        "donation": "रविवार को गेहूं, गुड़ या तांबे से जुड़ा दान करें।",
    },
    2: {
        "deity": "Chandra (Moon)",
        "mantra_sanskrit": "ॐ सोम सोमाय नमः",
        "mantra_english": "Om Som Somaya Namaha",
        "donation": "सोमवार को चावल, दूध या सफेद मिठाई दान करें।",
    },
    3: {
        "deity": "Guru (Jupiter)",
        "mantra_sanskrit": "ॐ बृहस्पतये नमः",
        "mantra_english": "Om Brihaspataye Namaha",
        "donation": "पीली दाल, हल्दी या पीली मिठाई दान करें।",
    },
    4: {
        "deity": "Rahu",
        "mantra_sanskrit": "ॐ राहवे नमः",
        "mantra_english": "Om Rahave Namaha",
        "donation": "काला तिल, कंबल या जरूरतमंद को छाया-सहायता दान करें।",
    },
    5: {
        "deity": "Budh (Mercury)",
        "mantra_sanskrit": "ॐ बुं बुधाय नमः",
        "mantra_english": "Om Bum Budhaya Namaha",
        "donation": "हरी सब्जियां, मूंग या विद्यार्थी सहायता दान करें।",
    },
    6: {
        "deity": "Shukra (Venus)",
        "mantra_sanskrit": "ॐ शुक्राय नमः",
        "mantra_english": "Om Shukraya Namaha",
        "donation": "सफेद वस्त्र, चावल या स्त्री-सहायता से जुड़ा दान करें।",
    },
    7: {
        "deity": "Ketu",
        "mantra_sanskrit": "ॐ केतवे नमः",
        "mantra_english": "Om Ketave Namaha",
        "donation": "आवारा पशुओं को भोजन, कंबल या शांत सेवा दें।",
    },
    8: {
        "deity": "Shani",
        "mantra_sanskrit": "ॐ शं शनैश्चराय नमः",
        "mantra_english": "Om Sham Shanicharaya Namaha",
        "donation": "काले तिल, सरसों का तेल या श्रमिक सहायता दान करें।",
    },
    9: {
        "deity": "Mangal (Mars)",
        "mantra_sanskrit": "ॐ क्रां क्रीं क्रौं सः भौमाय नमः",
        "mantra_english": "Om Kraam Kreem Kraum Sah Bhaumaya Namaha",
        "donation": "लाल मसूर, रक्तदान सहयोग या साहसिक सेवा से जुड़ा दान करें।",
    },
}

NUMBER_COLORS = {
    1: "Gold / Orange",
    2: "White / Silver",
    3: "Yellow",
    4: "Electric Blue",
    5: "Green",
    6: "Light Blue / Pink",
    7: "Grey / Smoky White",
    8: "Dark Blue / Black",
    9: "Red",
}

HABIT_FOCUS = {
    "life_stability_index": "daily routine और sleep-wake consistency को stabilize करना",
    "financial_discipline_index": "money review, saving rule और spending boundaries को मजबूत बनाना",
    "emotional_regulation_index": "breathwork, recovery breaks और calm-response practice को deepen करना",
    "dharma_alignment_score": "daily priorities को long-term purpose के साथ align करना",
    "confidence_score": "decision journal और clarity ritual को improve करना",
}


def _weakest_metric(scores: Optional[Dict[str, Any]]) -> str:
    if not scores:
        return "life_stability_index"

    candidates = [
        "life_stability_index",
        "financial_discipline_index",
        "emotional_regulation_index",
        "dharma_alignment_score",
        "confidence_score",
    ]
    resolved = []
    for key in candidates:
        try:
            resolved.append((key, int(scores.get(key, 50))))
        except (TypeError, ValueError):
            resolved.append((key, 50))
    return min(resolved, key=lambda item: item[1])[0]


def _focus_message(metric_key: str) -> str:
    return HABIT_FOCUS.get(metric_key, HABIT_FOCUS["life_stability_index"])


def generate_mobile_remedies(number: int, mobile_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    color = NUMBER_COLORS.get(number, "Neutral")
    supportive = (mobile_analysis or {}).get("supportive_number_energies") or []
    supportive_text = ", ".join(str(value) for value in supportive[:3]) if supportive else "1, 3, 5"

    return {
        "mobile_cover_color": color,
        "mobile_wallpaper": "ऐसा calm geometric या sacred-symbol wallpaper रखें जो distraction कम करे और focus को steady बनाए।",
        "charging_direction": "फोन को East या North facing दिशा में charge करना grounding signal के रूप में उपयोगी हो सकता है।",
        "whatsapp_dp": "DP simple, clear और confident रखें ताकि digital identity clutter-free रहे।",
        "mobile_usage_timing": "Heavy decisions रात में avoid करें; important calls और planning को morning या early evening में रखें।",
        "number_energy_hint": f"Supportive ending energies: {supportive_text}. यहां वास्तविक phone number generate नहीं किया गया है, केवल favorable energies दी गई हैं।",
    }


def generate_lifestyle_remedies(number: int, weakest_metric: str) -> Dict[str, Any]:
    color = NUMBER_COLORS.get(number, "balancing colors")
    focus_area = _focus_message(weakest_metric)

    return {
        "bracelet_suggestion": f"Number {number} aligned shades ({color}) का subtle bracelet, pen, notebook या accessory anchor की तरह उपयोग कर सकते हैं।",
        "daily_routine": f"आपके लिए सबसे महत्वपूर्ण habit है {focus_area}। इसे random mood पर नहीं बल्कि fixed time block पर चलाएं।",
        "meditation": "रोज 10 मिनट focused breathing, mantra stillness या quiet observation practice रखें।",
        "color_alignment": f"Workspace और clothing में {color} tones use करना आपकी energy को visually more aligned और less noisy महसूस करा सकता है।",
        "habit_recommendation": f"अगले 21 दिनों के लिए ऐसा repeatable ritual बनाएं जो {focus_area} पर सीधे काम करे।",
    }


def generate_vedic_remedies(number: int, weakest_metric: str) -> Dict[str, Any]:
    mantra_data = NUMBER_MANTRAS.get(number)
    if not mantra_data:
        return {}

    focus_area = _focus_message(weakest_metric)
    return {
        "deity": mantra_data["deity"],
        "mantra_sanskrit": mantra_data["mantra_sanskrit"],
        "mantra_pronunciation": mantra_data["mantra_english"],
        "recommended_donation": mantra_data["donation"],
        "practice_guideline": "21 दिनों तक रोज 108 repetitions करें। बेहतर होगा कि हर सुबह लगभग एक ही समय पर यह practice पूरी करें।",
        "purpose": f"इस remedy का उद्देश्य {focus_area} और inner alignment को support करना है।",
        "planetary_alignment": f"Number {number} की planetary energy को disciplined routine के साथ harmonize करना इस remedy का मुख्य focus है।",
    }


def generate_daily_energy_alignment(number: int, weakest_metric: str) -> Dict[str, Any]:
    focus_area = _focus_message(weakest_metric)
    return {
        "morning": "सुबह 10-15 मिनट sunlight exposure, जल सेवन और breath reset के साथ दिन शुरू करें।",
        "breathing": "5 मिनट deep nasal breathing या box breathing से nervous system को steady करें।",
        "focus_routine": f"First work block से पहले एक clear intention लिखें। आज का main alignment focus: {focus_area}।",
        "evening_reset": "रात में screen slowdown, short gratitude note और next-day top-3 list के साथ mental clutter release करें।",
    }


def generate_remedy_protocol(
    numerology_core: Dict[str, Any],
    scores: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pythagorean = numerology_core.get("pythagorean", {})
    mobile_analysis = numerology_core.get("mobile_analysis", {})

    primary_number = pythagorean.get("life_path_number") or pythagorean.get("destiny_number") or 0
    if not primary_number:
        return {}

    weakest_metric = _weakest_metric(scores)
    return {
        "lifestyle_remedies": generate_lifestyle_remedies(primary_number, weakest_metric),
        "mobile_remedies": generate_mobile_remedies(primary_number, mobile_analysis=mobile_analysis),
        "vedic_remedies": generate_vedic_remedies(primary_number, weakest_metric),
        "daily_energy_alignment": generate_daily_energy_alignment(primary_number, weakest_metric),
    }
