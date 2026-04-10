from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


SUPPORTED_LANGUAGE_PREFERENCE = Literal["hinglish", "hindi", "english"]
SUPPORTED_GENDER = Literal["male", "female", "other"]
SUPPORTED_CAREER_TYPE = Literal["business", "job"]
SUPPORTED_ROLE = Literal["entrepreneur", "employee", "consultant", "student"]
SUPPORTED_WILLINGNESS_TO_CHANGE = Literal["yes", "no", "undecided"]


def _derive_life_focus(primary_goal: Optional[str], career_type: Optional[str]) -> str:
    goal = (primary_goal or "").strip().lower()
    career = (career_type or "").strip().lower()

    if career == "business":
        return "business_decision"

    keyword_map = {
        "finance_debt": ["finance", "money", "debt", "loan", "cash", "income", "wealth"],
        "career_growth": ["career", "job", "promotion", "growth", "profession", "role"],
        "relationship": ["relationship", "marriage", "love", "partner", "family"],
        "health_stability": ["health", "fitness", "sleep", "wellness"],
        "emotional_confusion": ["anxiety", "emotion", "confusion", "clarity", "stress"],
        "business_decision": ["business", "startup", "company", "venture", "brand"],
    }

    for focus, keywords in keyword_map.items():
        if any(keyword in goal for keyword in keywords):
            return focus

    return "general_alignment"


def _map_career_role(career_type: Optional[str]) -> Optional[str]:
    career = (career_type or "").strip().lower()
    if career == "business":
        return "entrepreneur"
    if career == "job":
        return "employee"
    return None


def _normalize_date(raw_date: Optional[str]) -> Optional[str]:
    if not raw_date:
        return raw_date

    text = str(raw_date).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def _coerce_string_list(raw_value: Any) -> List[str]:
    if raw_value in (None, ""):
        return []
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    text = str(raw_value).strip()
    if not text:
        return []
    if "|" in text:
        return [item.strip() for item in text.split("|") if item.strip()]
    if "," in text:
        return [item.strip() for item in text.split(",") if item.strip()]
    return [text]


def _map_priority_focus(raw_focus: Any) -> Optional[str]:
    text = str(raw_focus or "").strip().lower()
    mapping = {
        "career": "career_growth",
        "money": "finance_debt",
        "finance": "finance_debt",
        "relationship": "relationship",
        "health": "health_stability",
        "business": "business_decision",
    }
    return mapping.get(text)


def _normalize_plan_key(raw_plan: Any) -> str:
    text = str(raw_plan or "").strip().lower()
    aliases = {
        "basic": "basic",
        "pro": "standard",
        "standard": "standard",
        "premium": "enterprise",
        "enterprise": "enterprise",
    }
    return aliases.get(text, "")


class BasicIdentity(BaseModel):
    full_name: str = Field(..., min_length=2)
    date_of_birth: str
    gender: Optional[SUPPORTED_GENDER] = None
    country_of_residence: str = Field(..., min_length=2)
    email: Optional[str] = None
    partner_name: Optional[str] = None
    business_name: Optional[str] = None
    signature_style: Optional[str] = None
    name_variations: Optional[str] = None

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender(cls, value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        normalized = str(value).strip().lower()
        if normalized.startswith("m"):
            return "male"
        if normalized.startswith("f"):
            return "female"
        if normalized.startswith("o"):
            return "other"
        return normalized


class BirthDetails(BaseModel):
    date_of_birth: str
    time_of_birth: Optional[str] = None
    birthplace_city: Optional[str] = None
    birthplace_country: Optional[str] = None


class FocusArea(BaseModel):
    life_focus: Literal[
        "finance_debt",
        "career_growth",
        "relationship",
        "health_stability",
        "emotional_confusion",
        "business_decision",
        "general_alignment",
    ]


class ContactLayer(BaseModel):
    mobile_number: Optional[str] = None
    social_handle: Optional[str] = None
    domain_handle: Optional[str] = None
    residence_number: Optional[str] = None
    vehicle_number: Optional[str] = None

    @field_validator("mobile_number", mode="before")
    @classmethod
    def _normalize_mobile_number(cls, value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        digits = "".join(char for char in str(value) if char.isdigit())
        if len(digits) != 10:
            raise ValueError("mobile_number must be a 10-digit number")
        return digits


class FinancialSnapshot(BaseModel):
    monthly_income: Optional[int] = None
    savings_ratio: Optional[int] = Field(None, ge=0, le=100)
    debt_ratio: Optional[int] = Field(None, ge=0, le=100)
    risk_tolerance: Optional[Literal["low", "moderate", "high"]] = None


class CareerProfile(BaseModel):
    industry: Optional[str] = None
    role: Optional[SUPPORTED_ROLE] = None
    years_experience: Optional[int] = None
    stress_level: Optional[int] = Field(None, ge=1, le=10)


class EmotionalState(BaseModel):
    anxiety_level: Optional[int] = Field(None, ge=1, le=10)
    decision_confusion: Optional[int] = Field(None, ge=1, le=10)
    impulse_control: Optional[int] = Field(None, ge=1, le=10)
    emotional_stability: Optional[int] = Field(None, ge=1, le=10)


class LifeEvents(BaseModel):
    positive_events_years: Optional[List[int]] = None
    setback_events_years: Optional[List[int]] = None


class BusinessHistory(BaseModel):
    major_investments: Optional[int] = None
    major_losses: Optional[int] = None
    risk_mistakes_count: Optional[int] = None


class HealthLifestyle(BaseModel):
    sleep_hours: Optional[int] = None
    alcohol: Optional[bool] = None
    smoking: Optional[bool] = None
    exercise_frequency_per_week: Optional[int] = None
    food_pattern: Optional[Literal["veg", "non_veg", "mixed"]] = None
    health_concerns: Optional[str] = None


class CalibrationAnswers(BaseModel):
    stress_response: Optional[Literal["withdraw", "impulsive", "overthink", "take_control"]] = None
    money_decision_style: Optional[Literal["emotional", "calculated", "risky", "avoidant"]] = None
    biggest_weakness: Optional[Literal["discipline", "patience", "confidence", "focus"]] = None
    life_preference: Optional[Literal["stability", "growth", "recognition", "freedom"]] = None
    decision_style: Optional[Literal["fast", "research", "advice", "emotional"]] = None

    @staticmethod
    def _normalize(value: Any) -> str:
        return str(value or "").strip().lower().replace("_", " ").replace("-", " ")

    @field_validator("stress_response", mode="before")
    @classmethod
    def _map_stress_response(cls, value: Any) -> Any:
        text = cls._normalize(value)
        if not text:
            return None
        if text in {"withdraw", "impulsive", "overthink"}:
            return text
        if text == "take control":
            return "take_control"
        if any(token in text for token in ("withdraw", "avoid", "silent", "shutdown")):
            return "withdraw"
        if any(token in text for token in ("impulse", "angry", "react")):
            return "impulsive"
        if any(token in text for token in ("overthink", "worry", "anxious")):
            return "overthink"
        if any(token in text for token in ("control", "plan", "take charge", "discipline")):
            return "take_control"
        return None

    @field_validator("money_decision_style", mode="before")
    @classmethod
    def _map_money_decision_style(cls, value: Any) -> Any:
        text = cls._normalize(value)
        if not text:
            return None
        if text in {"emotional", "calculated", "risky", "avoidant"}:
            return text
        if any(token in text for token in ("emotion", "feeling", "heart")):
            return "emotional"
        if any(token in text for token in ("calcul", "analysis", "planned", "safe")):
            return "calculated"
        if any(token in text for token in ("risk", "aggressive", "speculat")):
            return "risky"
        if any(token in text for token in ("avoid", "delay", "postpone")):
            return "avoidant"
        return None

    @field_validator("biggest_weakness", mode="before")
    @classmethod
    def _map_biggest_weakness(cls, value: Any) -> Any:
        text = cls._normalize(value)
        if not text:
            return None
        if text in {"discipline", "patience", "confidence", "focus"}:
            return text
        if any(token in text for token in ("discipline", "routine", "consisten")):
            return "discipline"
        if any(token in text for token in ("patience", "wait")):
            return "patience"
        if any(token in text for token in ("confidence", "self doubt", "fear")):
            return "confidence"
        if any(token in text for token in ("focus", "distraction", "attention")):
            return "focus"
        return None

    @field_validator("life_preference", mode="before")
    @classmethod
    def _map_life_preference(cls, value: Any) -> Any:
        text = cls._normalize(value)
        if not text:
            return None
        if text in {"stability", "growth", "recognition", "freedom"}:
            return text
        if any(token in text for token in ("stability", "secure", "safety")):
            return "stability"
        if any(token in text for token in ("growth", "scale", "expand", "improve")):
            return "growth"
        if any(token in text for token in ("recognition", "status", "respect", "name")):
            return "recognition"
        if any(token in text for token in ("freedom", "independ", "flexib")):
            return "freedom"
        return None

    @field_validator("decision_style", mode="before")
    @classmethod
    def _map_decision_style(cls, value: Any) -> Any:
        text = cls._normalize(value)
        if not text:
            return None
        if text in {"fast", "research", "advice", "emotional"}:
            return text
        if any(token in text for token in ("fast", "quick", "immediate")):
            return "fast"
        if any(token in text for token in ("research", "analy", "data")):
            return "research"
        if any(token in text for token in ("advice", "mentor", "consult", "expert")):
            return "advice"
        if any(token in text for token in ("emotion", "feeling", "intuition")):
            return "emotional"
        return None


class ReportPreferences(BaseModel):
    language_preference: SUPPORTED_LANGUAGE_PREFERENCE = "hindi"
    profession: Optional[str] = None
    relationship_status: Optional[str] = None
    career_type: Optional[SUPPORTED_CAREER_TYPE] = None
    primary_goal: Optional[str] = None
    willingness_to_change: SUPPORTED_WILLINGNESS_TO_CHANGE = "undecided"

    @field_validator("willingness_to_change", mode="before")
    @classmethod
    def _normalize_willingness_to_change(cls, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if not normalized:
            return "undecided"
        if normalized in {"yes", "y", "ready", "change", "willing"}:
            return "yes"
        if normalized in {"no", "n", "not now", "keep", "unwilling"}:
            return "no"
        return "undecided"


class LifeSignifyRequest(BaseModel):
    identity: BasicIdentity
    birth_details: BirthDetails
    focus: FocusArea
    current_problem: Optional[str] = None
    contact: Optional[ContactLayer] = None
    financial: Optional[FinancialSnapshot] = None
    career: Optional[CareerProfile] = None
    emotional: Optional[EmotionalState] = None
    life_events: Optional[LifeEvents] = None
    business_history: Optional[BusinessHistory] = None
    health: Optional[HealthLifestyle] = None
    calibration: Optional[CalibrationAnswers] = None
    preferences: Optional[ReportPreferences] = None
    plan_override: Optional[Literal["basic", "pro", "standard", "premium", "enterprise"]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        data = dict(value)
        has_nested_contract = any(data.get(key) for key in ("identity", "birth_details", "focus"))

        flat_name = data.get("name") or data.get("full_name")
        flat_dob = data.get("dob") or data.get("date_of_birth")
        flat_mobile = data.get("mobile_number")
        flat_gender = data.get("gender")
        flat_city = data.get("city")
        flat_country = data.get("country")
        flat_email = data.get("email")
        flat_language = data.get("language_preference")
        flat_profession = data.get("profession")
        flat_relationship_status = data.get("relationship_status")
        flat_career_type = data.get("career_type")
        flat_willingness_to_change = data.get("willingness_to_change")
        flat_name_variations_raw = data.get("name_variations") or data.get("name_variation")
        flat_name_variations = _coerce_string_list(flat_name_variations_raw)
        flat_birth_time = data.get("birth_time")
        flat_birth_place = data.get("birth_place")
        flat_goals = _coerce_string_list(data.get("goals") or data.get("primary_goal"))
        flat_current_issues = _coerce_string_list(data.get("current_issues"))
        flat_priority_focus = data.get("priority_focus")
        flat_specific_question = data.get("specific_question")
        flat_current_status = data.get("current_status") or {}

        plan_key = _normalize_plan_key(data.get("plan_override"))
        if not plan_key:
            has_premium_fields = any(
                data.get(key) not in (None, "", [], {})
                for key in ("birth_time", "birth_place", "goals", "priority_focus", "current_status")
            )
            if has_premium_fields:
                plan_key = "enterprise"
            elif flat_name_variations or flat_current_issues or flat_gender:
                plan_key = "standard"
            else:
                plan_key = "basic"
            data["plan_override"] = plan_key

        if not has_nested_contract:
            required_map: Dict[str, Any] = {
                "name": flat_name,
                "dob": flat_dob,
                "mobile_number": flat_mobile,
            }
            if plan_key in {"standard", "enterprise"}:
                required_map["name_variations"] = flat_name_variations
            if plan_key == "enterprise":
                required_map["birth_time"] = flat_birth_time
                required_map["birth_place"] = flat_birth_place
                required_map["goals"] = flat_goals
                required_map["priority_focus"] = flat_priority_focus

            missing = [field for field, field_value in required_map.items() if field_value in (None, "", [], {})]
            if missing:
                joined = ", ".join(missing)
                raise ValueError(f"Missing required report fields: {joined}")

            if plan_key == "enterprise":
                birth_place_text = str(flat_birth_place or "").strip()
                if birth_place_text and "," not in birth_place_text:
                    raise ValueError("birth_place must be in 'city, country' format")
                if not _map_priority_focus(flat_priority_focus):
                    raise ValueError("priority_focus must be one of: career, money, relationship, health")

        identity = dict(data.get("identity") or {})
        birth_details = dict(data.get("birth_details") or {})
        focus = dict(data.get("focus") or {})
        contact = dict(data.get("contact") or {})
        career = dict(data.get("career") or {})
        preferences = dict(data.get("preferences") or {})

        if flat_name and not identity.get("full_name"):
            identity["full_name"] = flat_name
        if flat_dob:
            identity.setdefault("date_of_birth", flat_dob)
            birth_details.setdefault("date_of_birth", flat_dob)
        if identity.get("date_of_birth"):
            identity["date_of_birth"] = _normalize_date(identity.get("date_of_birth"))
        if birth_details.get("date_of_birth"):
            birth_details["date_of_birth"] = _normalize_date(birth_details.get("date_of_birth"))
        if flat_gender and not identity.get("gender"):
            identity["gender"] = flat_gender
        if flat_country:
            identity.setdefault("country_of_residence", flat_country)
            birth_details.setdefault("birthplace_country", flat_country)
        else:
            identity.setdefault("country_of_residence", "India")
            birth_details.setdefault("birthplace_country", "India")
        if flat_email and not identity.get("email"):
            identity["email"] = flat_email
        normalized_variations = " | ".join(flat_name_variations) if flat_name_variations else None
        if normalized_variations and not identity.get("name_variations"):
            identity["name_variations"] = normalized_variations
        if flat_city and not birth_details.get("birthplace_city"):
            birth_details["birthplace_city"] = flat_city
        if flat_mobile and not contact.get("mobile_number"):
            contact["mobile_number"] = flat_mobile

        if flat_birth_time and not birth_details.get("time_of_birth"):
            birth_details["time_of_birth"] = str(flat_birth_time).strip()

        if flat_birth_place and not birth_details.get("birthplace_city"):
            birth_place_text = str(flat_birth_place).strip()
            if "," in birth_place_text:
                city, country = [part.strip() for part in birth_place_text.split(",", 1)]
                if city:
                    birth_details["birthplace_city"] = city
                if country and not birth_details.get("birthplace_country"):
                    birth_details["birthplace_country"] = country
                    identity.setdefault("country_of_residence", country)
            elif birth_place_text:
                birth_details["birthplace_city"] = birth_place_text

        if isinstance(flat_current_status, dict):
            relationship_from_status = str(flat_current_status.get("relationship") or "").strip()
            if relationship_from_status and not preferences.get("relationship_status"):
                preferences["relationship_status"] = relationship_from_status
            career_status = str(flat_current_status.get("career") or "").strip()
            if career_status and not career.get("industry"):
                career["industry"] = f"status:{career_status}"

        if flat_profession and not career.get("industry"):
            career["industry"] = flat_profession
        derived_role = _map_career_role(flat_career_type)
        if derived_role and not career.get("role"):
            career["role"] = derived_role

        if flat_language and not preferences.get("language_preference"):
            preferences["language_preference"] = flat_language
        if flat_profession and not preferences.get("profession"):
            preferences["profession"] = flat_profession
        if flat_relationship_status and not preferences.get("relationship_status"):
            preferences["relationship_status"] = flat_relationship_status
        if flat_career_type and not preferences.get("career_type"):
            preferences["career_type"] = flat_career_type
        if flat_goals and not preferences.get("primary_goal"):
            preferences["primary_goal"] = " | ".join(flat_goals)
        if flat_willingness_to_change and not preferences.get("willingness_to_change"):
            preferences["willingness_to_change"] = flat_willingness_to_change

        mapped_priority_focus = _map_priority_focus(flat_priority_focus)
        if mapped_priority_focus and not focus.get("life_focus"):
            focus["life_focus"] = mapped_priority_focus

        if not data.get("current_problem") and flat_current_issues:
            data["current_problem"] = ", ".join(flat_current_issues)
        if flat_specific_question:
            question = str(flat_specific_question).strip()
            if question:
                existing_problem = str(data.get("current_problem") or "").strip()
                if existing_problem:
                    data["current_problem"] = f"{existing_problem} | {question}"
                else:
                    data["current_problem"] = question

        if not focus.get("life_focus"):
            focus["life_focus"] = _derive_life_focus(
                primary_goal=preferences.get("primary_goal") or data.get("current_problem"),
                career_type=preferences.get("career_type"),
            )

        if not str(preferences.get("willingness_to_change") or "").strip():
            preferences["willingness_to_change"] = "undecided"

        if preferences.get("primary_goal") and not data.get("current_problem"):
            data["current_problem"] = preferences.get("primary_goal")
        if not str(data.get("current_problem") or "").strip():
            data["current_problem"] = "consistency"

        data["identity"] = identity
        data["birth_details"] = birth_details
        data["focus"] = focus
        if contact:
            data["contact"] = contact
        if career:
            data["career"] = career
        if preferences:
            data["preferences"] = preferences

        return data

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "examples": [
                {
                    "plan_override": "basic",
                    "name": "Aarav Sharma",
                    "dob": "1992-08-14",
                    "mobile_number": "9876543210",
                },
                {
                    "plan_override": "standard",
                    "name": "Aarav Sharma",
                    "dob": "1992-08-14",
                    "mobile_number": "9876543210",
                    "name_variations": ["Aarav", "Aarav Sharma"],
                    "gender": "male",
                    "current_issues": ["career", "money", "relationship"],
                },
                {
                    "plan_override": "enterprise",
                    "name": "Aarav Sharma",
                    "dob": "1992-08-14",
                    "mobile_number": "9876543210",
                    "name_variations": ["Aarav", "Aarav Sharma"],
                    "birth_time": "07:30",
                    "birth_place": "Lucknow, India",
                    "goals": ["career_growth", "wealth", "relationship", "health"],
                    "current_status": {
                        "career": "growing",
                        "relationship": "single",
                        "financial": "unstable",
                    },
                    "priority_focus": "money",
                    "specific_question": "How should I stabilize finances in next 90 days?",
                }
            ]
        },
    }
