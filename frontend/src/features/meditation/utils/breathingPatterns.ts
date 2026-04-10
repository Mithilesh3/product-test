export type BreathingMode = "box" | "abdominal" | "om";
export type BreathingPhaseId = "inhale" | "hold" | "exhale" | "chant_om" | "silence";
export type LanguageMode = "en" | "hi" | "both";

export interface LocalizedText {
  en: string;
  hi: string;
}

export interface BreathingPhase {
  id: BreathingPhaseId;
  label: LocalizedText;
  seconds: number;
}

export interface YogaGuidance {
  yogaName: LocalizedText;
  instruction: LocalizedText;
}

export interface BreathingPreset {
  mode: BreathingMode;
  title: string;
  subtitle: string | ((omDurationSec: number) => string);
}

export const BOX_PHASE_OPTIONS = [4, 5, 6] as const;
export const ABDOMINAL_INHALE_OPTIONS = [4, 5, 6] as const;
export const OM_DURATION_OPTIONS = [6, 9, 12, 15, 21] as const;

const normalizeToAllowed = (value: number, allowed: readonly number[], fallback: number) =>
  allowed.includes(value) ? value : fallback;

export const getDurationOptionsForMode = (mode: BreathingMode): number[] => {
  if (mode === "box") return [...BOX_PHASE_OPTIONS];
  if (mode === "abdominal") return [...ABDOMINAL_INHALE_OPTIONS];
  return [...OM_DURATION_OPTIONS];
};

export const getDefaultDurationForMode = (mode: BreathingMode): number => {
  if (mode === "box") return BOX_PHASE_OPTIONS[0];
  if (mode === "abdominal") return ABDOMINAL_INHALE_OPTIONS[0];
  return OM_DURATION_OPTIONS[3];
};

export const getBreathingPattern = (mode: BreathingMode, omDurationSec: number): BreathingPhase[] => {
  if (mode === "box") {
    const phaseSeconds = normalizeToAllowed(omDurationSec, BOX_PHASE_OPTIONS, BOX_PHASE_OPTIONS[0]);
    return [
      { id: "inhale", label: { en: "Inhale", hi: "श्वास लें" }, seconds: phaseSeconds },
      { id: "hold", label: { en: "Hold", hi: "रोकें" }, seconds: phaseSeconds },
      { id: "exhale", label: { en: "Exhale", hi: "श्वास छोड़ें" }, seconds: phaseSeconds },
      { id: "hold", label: { en: "Hold", hi: "रोकें" }, seconds: phaseSeconds },
    ];
  }

  if (mode === "abdominal") {
    const inhaleSeconds = normalizeToAllowed(
      omDurationSec,
      ABDOMINAL_INHALE_OPTIONS,
      ABDOMINAL_INHALE_OPTIONS[0],
    );
    return [
      { id: "inhale", label: { en: "Inhale", hi: "श्वास लें" }, seconds: inhaleSeconds },
      { id: "exhale", label: { en: "Exhale", hi: "श्वास छोड़ें" }, seconds: inhaleSeconds + 2 },
    ];
  }

  if (mode === "om") {
    return [
      { id: "inhale", label: { en: "Inhale", hi: "श्वास लें" }, seconds: 4 },
      { id: "chant_om", label: { en: "Chant OM", hi: "ॐ जप" }, seconds: omDurationSec },
      { id: "silence", label: { en: "Silence", hi: "मौन" }, seconds: 2 },
    ];
  }

  return [];
};

export const syncOmWithPhase = (phaseId: BreathingPhaseId, seconds: number) => {
  if (phaseId === "exhale" || phaseId === "chant_om") {
    return { playOm: true, durationSec: Math.max(1, seconds) };
  }
  return { playOm: false, durationSec: 0 };
};

export const BREATHING_PATTERNS: Record<BreathingMode, BreathingPhase[]> = {
  box: getBreathingPattern("box", BOX_PHASE_OPTIONS[0]),
  abdominal: getBreathingPattern("abdominal", ABDOMINAL_INHALE_OPTIONS[0]),
  om: [
    { id: "inhale", label: { en: "Inhale", hi: "श्वास लें" }, seconds: 4 },
    { id: "chant_om", label: { en: "Chant OM", hi: "ॐ जप" }, seconds: 10 },
    { id: "silence", label: { en: "Silence", hi: "मौन" }, seconds: 2 },
  ],
};

export const YOGA_GUIDANCE_BY_MODE: Record<BreathingMode, YogaGuidance> = {
  box: {
    yogaName: {
      en: "Sukhasana (Easy Seated Pose)",
      hi: "सुखासन (सरल ध्यान आसन)",
    },
    instruction: {
      en: "Sit comfortably with spine straight.",
      hi: "रीढ़ सीधी रखते हुए आराम से बैठें।",
    },
  },
  abdominal: {
    yogaName: {
      en: "Pranayama (Breath Awareness)",
      hi: "प्राणायाम (श्वास जागरूकता)",
    },
    instruction: {
      en: "Inhale to expand belly, exhale to relax body.",
      hi: "श्वास लेते समय पेट फैलाएं, छोड़ते समय शरीर ढीला करें।",
    },
  },
  om: {
    yogaName: {
      en: "Gyan Mudra (Hand Gesture)",
      hi: "ज्ञान मुद्रा (हाथ की मुद्रा)",
    },
    instruction: {
      en: "Touch thumb and index finger, rest hands on knees.",
      hi: "अंगूठे और तर्जनी को मिलाएं, हाथ घुटनों पर रखें।",
    },
  },
};

export const BREATHING_PRESETS: BreathingPreset[] = [
  {
    mode: "box",
    title: "Box Breathing",
    subtitle: "4s inhale | 4s hold | 4s exhale | 4s hold",
  },
  {
    mode: "abdominal",
    title: "Abdominal Breathing",
    subtitle: "4s inhale | 6s exhale",
  },
  {
    mode: "om",
    title: "OM Chanting",
    subtitle: (omDurationSec) => `4s inhale | ${omDurationSec}s OM | 2s silence`,
  },
];

export const LANGUAGE_OPTIONS: Array<{ value: LanguageMode; label: string }> = [
  { value: "both", label: "EN + HI" },
  { value: "en", label: "English" },
  { value: "hi", label: "हिंदी" },
];

export const SESSION_DURATION_OPTIONS = [120, 180, 300];
