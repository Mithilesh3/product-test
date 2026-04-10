import { z } from "zod";

export type ReportPlanKey = "BASIC" | "STANDARD" | "ENTERPRISE";

export type ReportFieldKey =
  | "fullName"
  | "nameVariations"
  | "dateOfBirth"
  | "birthTime"
  | "gender"
  | "mobileNumber"
  | "email"
  | "businessName"
  | "signatureStyle"
  | "focusArea"
  | "language"
  | "occupation"
  | "relationshipStatus"
  | "concernPrimary"
  | "concernSecondary"
  | "incomeRangeMonthly"
  | "stressLevel"
  | "workMode"
  | "maritalStatus"
  | "industry"
  | "employmentType"
  | "incomeRangeAnnual"
  | "debtRange"
  | "goal1"
  | "goal2"
  | "goal3"
  | "challenge1"
  | "challenge2"
  | "challenge3"
  | "reportEmphasis"
  | "healthConcerns"
  | "city"
  | "birthCountry"
  | "socialHandle"
  | "domainHandle"
  | "residenceNumber"
  | "vehicleNumber"
  | "spiritualPreference"
  | "willingnessToChange";

export interface ReportFormState {
  plan: ReportPlanKey;
  fullName: string;
  nameVariations: string;
  dateOfBirth: string;
  birthTime: string;
  gender: string;
  mobileNumber: string;
  email: string;
  businessName: string;
  signatureStyle: string;
  focusArea: string;
  language: string;
  occupation: string;
  relationshipStatus: string;
  concernPrimary: string;
  concernSecondary: string;
  incomeRangeMonthly: string;
  stressLevel: string;
  workMode: string;
  maritalStatus: string;
  industry: string;
  employmentType: string;
  incomeRangeAnnual: string;
  debtRange: string;
  goal1: string;
  goal2: string;
  goal3: string;
  challenge1: string;
  challenge2: string;
  challenge3: string;
  reportEmphasis: string;
  healthConcerns: string;
  city: string;
  birthCountry: string;
  socialHandle: string;
  domainHandle: string;
  residenceNumber: string;
  vehicleNumber: string;
  spiritualPreference: string;
  willingnessToChange: string;
}

export const createInitialReportFormState = (mobile = "", fullName = "", email = ""): ReportFormState => ({
  plan: "BASIC",
  fullName,
  nameVariations: "",
  dateOfBirth: "",
  birthTime: "",
  gender: "",
  mobileNumber: mobile,
  email,
  businessName: "",
  signatureStyle: "",
  focusArea: "general_alignment",
  language: "hindi",
  occupation: "",
  relationshipStatus: "",
  concernPrimary: "",
  concernSecondary: "",
  incomeRangeMonthly: "",
  stressLevel: "",
  workMode: "",
  maritalStatus: "",
  industry: "",
  employmentType: "",
  incomeRangeAnnual: "",
  debtRange: "",
  goal1: "",
  goal2: "",
  goal3: "",
  challenge1: "",
  challenge2: "",
  challenge3: "",
  reportEmphasis: "",
  healthConcerns: "",
  city: "",
  birthCountry: "",
  socialHandle: "",
  domainHandle: "",
  residenceNumber: "",
  vehicleNumber: "",
  spiritualPreference: "",
  willingnessToChange: "undecided",
});

const basicFields: ReportFieldKey[] = [
  "fullName",
  "dateOfBirth",
  "gender",
  "mobileNumber",
  "city",
  "concernPrimary",
  "willingnessToChange",
];

const standardFields: ReportFieldKey[] = [
  ...basicFields,
  "nameVariations",
  "email",
  "businessName",
  "signatureStyle",
  "occupation",
  "relationshipStatus",
  "concernSecondary",
];

const enterpriseFields: ReportFieldKey[] = [
  ...standardFields,
  "focusArea",
  "language",
  "incomeRangeMonthly",
  "stressLevel",
  "workMode",
  "industry",
  "employmentType",
  "incomeRangeAnnual",
  "debtRange",
  "goal1",
  "goal2",
  "goal3",
  "challenge1",
  "challenge2",
  "challenge3",
  "reportEmphasis",
  "healthConcerns",
  "birthTime",
  "birthCountry",
  "socialHandle",
  "domainHandle",
  "residenceNumber",
  "vehicleNumber",
  "spiritualPreference",
];

const _unique = (fields: ReportFieldKey[]): ReportFieldKey[] => Array.from(new Set(fields));

export const planVisibleFields: Record<ReportPlanKey, ReportFieldKey[]> = {
  BASIC: _unique(basicFields),
  STANDARD: _unique(standardFields),
  ENTERPRISE: _unique(enterpriseFields),
};

export const planRequiredFields: Record<ReportPlanKey, ReportFieldKey[]> = {
  BASIC: ["fullName", "dateOfBirth", "mobileNumber"],
  STANDARD: [
    "fullName",
    "nameVariations",
    "dateOfBirth",
    "mobileNumber",
    "concernPrimary",
  ],
  ENTERPRISE: [
    "fullName",
    "nameVariations",
    "dateOfBirth",
    "mobileNumber",
    "birthTime",
    "city",
    "goal1",
    "focusArea",
    "concernPrimary",
  ],
};

const commonSchema = z.object({
  fullName: z.string().min(2, "Full Name is required"),
  nameVariations: z.string().optional(),
  dateOfBirth: z.string().min(1, "Date of Birth is required"),
  birthTime: z.string().optional(),
  gender: z.string().optional(),
  mobileNumber: z
    .string()
    .regex(/^\d{10}$/, "Mobile number must be exactly 10 digits"),
  email: z.string().email("Valid email is required").or(z.literal("")),
  businessName: z.string().optional(),
  signatureStyle: z.string().optional(),
  focusArea: z.string().optional(),
  language: z.string().optional(),
  concernPrimary: z.string().optional(),
  city: z.string().optional(),
  birthCountry: z.string().optional(),
  socialHandle: z.string().optional(),
  domainHandle: z.string().optional(),
  residenceNumber: z.string().optional(),
  vehicleNumber: z.string().optional(),
  willingnessToChange: z.enum(["yes", "no", "undecided"]),
});

const standardExtendedSchema = commonSchema.extend({
  occupation: z.string().optional(),
  relationshipStatus: z.string().optional(),
  concernPrimary: z.string().optional(),
  incomeRangeMonthly: z.string().optional(),
  stressLevel: z.string().optional(),
  workMode: z.string().optional(),
});

const standardSchema = commonSchema;

const enterpriseSchema = standardExtendedSchema.extend({
  maritalStatus: z.string().optional(),
  industry: z.string().optional(),
  employmentType: z.string().optional(),
  incomeRangeAnnual: z.string().optional(),
  debtRange: z.string().optional(),
  goal1: z.string().optional(),
  challenge1: z.string().optional(),
  reportEmphasis: z.string().optional(),
  healthConcerns: z.string().optional(),
  city: z.string().min(1, "City is required"),
});

export const planValidationSchemas: Record<ReportPlanKey, z.ZodTypeAny> = {
  BASIC: commonSchema,
  STANDARD: standardSchema.extend({
    nameVariations: z.string().min(2, "Name variations are required"),
    concernPrimary: z.string().min(2, "At least one current issue is required"),
  }),
  ENTERPRISE: enterpriseSchema.extend({
    nameVariations: z.string().min(2, "Name variations are required"),
    goal1: z.string().min(2, "At least one goal is required"),
    birthTime: z.string().min(1, "Birth time is required"),
    focusArea: z.string().min(2, "Priority focus is required"),
    concernPrimary: z.string().min(2, "Specific issue/question is required"),
  }),
};

const mapFocus = (value: string): string => {
  const normalized = value.trim().toLowerCase();
  const supported = [
    "finance_debt",
    "career_growth",
    "relationship",
    "health_stability",
    "emotional_confusion",
    "business_decision",
    "general_alignment",
  ];
  return supported.includes(normalized) ? normalized : "general_alignment";
};

const mapGender = (value: string): "male" | "female" | "other" => {
  const normalized = (value || "").trim().toLowerCase();
  if (normalized === "male" || normalized === "female" || normalized === "other") {
    return normalized;
  }
  if (normalized.startsWith("m")) return "male";
  if (normalized.startsWith("f")) return "female";
  return "other";
};

const mapLanguage = (value: string): "hindi" | "english" | "hinglish" => {
  const normalized = (value || "").trim().toLowerCase();
  if (normalized === "hindi" || normalized === "english" || normalized === "hinglish") {
    return normalized;
  }
  if (normalized.includes("hing")) return "hinglish";
  if (normalized.includes("eng")) return "english";
  return "hindi";
};

const mapWillingnessToChange = (value: string): "yes" | "no" | "undecided" => {
  const normalized = (value || "").trim().toLowerCase();
  if (normalized === "yes" || normalized === "no" || normalized === "undecided") {
    return normalized;
  }
  if (normalized.startsWith("y")) return "yes";
  if (normalized.startsWith("n")) return "no";
  return "undecided";
};

const normalizeFreeText = (value: string): string =>
  (value || "").trim().toLowerCase().replace(/[_-]+/g, " ");

const includesAny = (value: string, keywords: string[]): boolean =>
  keywords.some((keyword) => value.includes(keyword));

const mapStressResponse = (
  value: string,
): "withdraw" | "impulsive" | "overthink" | "take_control" | undefined => {
  const normalized = normalizeFreeText(value);
  if (!normalized) return undefined;
  if (normalized === "withdraw" || normalized === "impulsive" || normalized === "overthink") {
    return normalized;
  }
  if (normalized === "take control") return "take_control";
  if (includesAny(normalized, ["withdraw", "avoid", "silent", "shut down"])) return "withdraw";
  if (includesAny(normalized, ["impulse", "angry", "react"])) return "impulsive";
  if (includesAny(normalized, ["overthink", "anxious", "worry"])) return "overthink";
  if (includesAny(normalized, ["control", "plan", "take charge", "discipline"])) return "take_control";
  return undefined;
};

const mapMoneyDecisionStyle = (
  value: string,
): "emotional" | "calculated" | "risky" | "avoidant" | undefined => {
  const normalized = normalizeFreeText(value);
  if (!normalized) return undefined;
  if (
    normalized === "emotional" ||
    normalized === "calculated" ||
    normalized === "risky" ||
    normalized === "avoidant"
  ) {
    return normalized;
  }
  if (includesAny(normalized, ["emotion", "feeling", "heart"])) return "emotional";
  if (includesAny(normalized, ["calcul", "analysis", "planned", "safe"])) return "calculated";
  if (includesAny(normalized, ["risk", "aggressive", "speculat"])) return "risky";
  if (includesAny(normalized, ["avoid", "delay", "postpone"])) return "avoidant";
  return undefined;
};

const mapBiggestWeakness = (
  value: string,
): "discipline" | "patience" | "confidence" | "focus" | undefined => {
  const normalized = normalizeFreeText(value);
  if (!normalized) return undefined;
  if (
    normalized === "discipline" ||
    normalized === "patience" ||
    normalized === "confidence" ||
    normalized === "focus"
  ) {
    return normalized;
  }
  if (includesAny(normalized, ["discipline", "routine", "consisten"])) return "discipline";
  if (includesAny(normalized, ["patience", "wait", "delay tolerance"])) return "patience";
  if (includesAny(normalized, ["confidence", "self doubt", "fear"])) return "confidence";
  if (includesAny(normalized, ["focus", "distraction", "attention"])) return "focus";
  return undefined;
};

const mapLifePreference = (
  value: string,
): "stability" | "growth" | "recognition" | "freedom" | undefined => {
  const normalized = normalizeFreeText(value);
  if (!normalized) return undefined;
  if (
    normalized === "stability" ||
    normalized === "growth" ||
    normalized === "recognition" ||
    normalized === "freedom"
  ) {
    return normalized;
  }
  if (includesAny(normalized, ["stability", "secure", "safety"])) return "stability";
  if (includesAny(normalized, ["growth", "scale", "expand", "improve"])) return "growth";
  if (includesAny(normalized, ["recognition", "respect", "status", "name"])) return "recognition";
  if (includesAny(normalized, ["freedom", "independ", "flexib"])) return "freedom";
  return undefined;
};

const mapDecisionStyle = (
  value: string,
): "fast" | "research" | "advice" | "emotional" | undefined => {
  const normalized = normalizeFreeText(value);
  if (!normalized) return undefined;
  if (
    normalized === "fast" ||
    normalized === "research" ||
    normalized === "advice" ||
    normalized === "emotional"
  ) {
    return normalized;
  }
  if (includesAny(normalized, ["fast", "quick", "immediate"])) return "fast";
  if (includesAny(normalized, ["research", "analy", "data"])) return "research";
  if (includesAny(normalized, ["advice", "mentor", "consult", "expert"])) return "advice";
  if (includesAny(normalized, ["emotion", "feeling", "intuition"])) return "emotional";
  return undefined;
};

const mapCareerType = (workMode: string): "job" | "business" => {
  const normalized = (workMode || "").toLowerCase();
  if (normalized.includes("business") || normalized.includes("self")) return "business";
  return "job";
};

const toInt = (value: string): number | undefined => {
  const digits = (value || "").replace(/[^0-9]/g, "");
  if (!digits) return undefined;
  const num = Number(digits);
  return Number.isNaN(num) ? undefined : num;
};

export const buildReportSubmitPayload = (state: ReportFormState) => {
  const mappedStressResponse = mapStressResponse(state.challenge1);
  const mappedMoneyDecisionStyle = mapMoneyDecisionStyle(state.challenge2);
  const mappedWeakness = mapBiggestWeakness(state.challenge3);
  const mappedLifePreference = mapLifePreference(state.goal1);
  const mappedDecisionStyle = mapDecisionStyle(state.reportEmphasis);
  const birthCity = (state.city || "").trim();
  const businessName = (state.businessName || "").trim();
  const signatureStyle = (state.signatureStyle || "").trim();
  const nameVariations = (state.nameVariations || "").trim();
  const birthTime = (state.birthTime || "").trim();
  const birthCountry = (state.birthCountry || "").trim();
  const socialHandle = (state.socialHandle || "").trim();
  const domainHandle = (state.domainHandle || "").trim();
  const residenceNumber = (state.residenceNumber || "").trim();
  const vehicleNumber = (state.vehicleNumber || "").trim();

  const normalizedPrimaryChallenge = (state.concernPrimary || "").trim() || "consistency";
  const genderValue = (state.gender || "").trim();
  const currentIssues = [state.concernPrimary, state.concernSecondary]
    .map((item) => (item || "").trim())
    .filter(Boolean);
  const goals = [state.goal1, state.goal2, state.goal3]
    .map((item) => (item || "").trim())
    .filter(Boolean);
  const nameVariationList = nameVariations
    ? nameVariations
        .split("|")
        .map((item) => item.trim())
        .filter(Boolean)
    : [];
  const birthPlace = [birthCity, birthCountry].filter(Boolean).join(", ");
  const mappedFocus = mapFocus(state.focusArea || "general_alignment");
  const priorityFocus =
    mappedFocus === "career_growth"
      ? "career"
      : mappedFocus === "finance_debt"
        ? "money"
        : mappedFocus === "relationship"
          ? "relationship"
          : mappedFocus === "health_stability"
            ? "health"
            : "career";
  return {
    // Flat contract (basic/standard/premium)
    name: state.fullName,
    dob: state.dateOfBirth,
    mobile_number: state.mobileNumber,
    ...(nameVariationList.length ? { name_variations: nameVariationList } : {}),
    ...(genderValue ? { gender: mapGender(genderValue) } : {}),
    ...(currentIssues.length ? { current_issues: currentIssues } : {}),
    ...(birthTime ? { birth_time: birthTime } : {}),
    ...(birthPlace ? { birth_place: birthPlace } : {}),
    ...(goals.length ? { goals } : {}),
    ...(state.plan === "ENTERPRISE"
      ? {
          current_status: {
            career: "growing",
            relationship: (state.relationshipStatus || state.maritalStatus || "single").toLowerCase(),
            financial: "unstable",
          },
          priority_focus: priorityFocus,
          specific_question: normalizedPrimaryChallenge,
        }
      : {}),

    // Nested contract (backward compatibility)
    identity: {
      full_name: state.fullName,
      date_of_birth: state.dateOfBirth,
      ...(genderValue ? { gender: mapGender(genderValue) } : {}),
      country_of_residence: "India",
      email: state.email,
      ...(businessName ? { business_name: businessName } : {}),
      ...(signatureStyle ? { signature_style: signatureStyle } : {}),
      ...(nameVariations ? { name_variations: nameVariations } : {}),
    },
    birth_details: {
      date_of_birth: state.dateOfBirth,
      ...(birthCity ? { birthplace_city: birthCity } : {}),
      ...(birthCountry ? { birthplace_country: birthCountry } : {}),
      ...(birthTime ? { time_of_birth: birthTime } : {}),
    },
    focus: {
      life_focus: mappedFocus,
    },
    current_problem: normalizedPrimaryChallenge,
    contact: {
      mobile_number: state.mobileNumber,
      ...(socialHandle ? { social_handle: socialHandle } : {}),
      ...(domainHandle ? { domain_handle: domainHandle } : {}),
      ...(residenceNumber ? { residence_number: residenceNumber } : {}),
      ...(vehicleNumber ? { vehicle_number: vehicleNumber } : {}),
    },
    financial: {
      monthly_income: toInt(state.incomeRangeMonthly),
      debt_ratio: toInt(state.debtRange),
    },
    career: {
      industry: state.industry || state.occupation,
      stress_level: toInt(state.stressLevel),
      role: mapCareerType(state.workMode) === "business" ? "entrepreneur" : "employee",
    },
    emotional: {
      anxiety_level: toInt(state.stressLevel),
    },
    health: {
      health_concerns: (state.healthConcerns || "").trim() || undefined,
    },
    calibration: {
      decision_style: mappedDecisionStyle,
      stress_response: mappedStressResponse,
      money_decision_style: mappedMoneyDecisionStyle,
      biggest_weakness: mappedWeakness,
      life_preference: mappedLifePreference,
    },
    preferences: {
      language_preference: mapLanguage(state.language || "hindi"),
      willingness_to_change: mapWillingnessToChange(state.willingnessToChange),
      profession: state.occupation || state.industry,
      relationship_status: state.relationshipStatus || state.maritalStatus,
      career_type: mapCareerType(state.workMode),
      primary_goal:
        goals.join(" | ") || normalizedPrimaryChallenge,
    },
    plan_override:
      state.plan === "BASIC"
        ? "basic"
        : state.plan === "STANDARD"
          ? "standard"
          : "enterprise",
  };
};
