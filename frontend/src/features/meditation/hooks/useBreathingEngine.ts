import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getBreathingPattern,
  getDefaultDurationForMode,
  getDurationOptionsForMode,
  LANGUAGE_OPTIONS,
  SESSION_DURATION_OPTIONS,
  YOGA_GUIDANCE_BY_MODE,
  syncOmWithPhase,
  type BreathingMode,
  type BreathingPhaseId,
  type LanguageMode,
  type LocalizedText,
} from "../utils/breathingPatterns";

interface EngineState {
  isRunning: boolean;
  isCountdown: boolean;
  countdownLeft: number;
  showSessionComplete: boolean;
  sessionSecondsLeft: number;
  phaseIndex: number;
  phaseSecondsLeft: number;
  phaseStep: number;
  sessionCompleteStep: number;
}

const SESSION_COMPLETE_HOLD_SECONDS = 2;
const PRE_START_COUNTDOWN_SECONDS = 3;

const createEngineState = (
  mode: BreathingMode,
  durationSec: number,
  omDurationSec: number,
  overrides?: Partial<EngineState>,
): EngineState => ({
  isRunning: false,
  isCountdown: false,
  countdownLeft: PRE_START_COUNTDOWN_SECONDS,
  showSessionComplete: false,
  sessionSecondsLeft: durationSec,
  phaseIndex: 0,
  phaseSecondsLeft: getBreathingPattern(mode, omDurationSec)[0].seconds,
  phaseStep: 0,
  sessionCompleteStep: 0,
  ...overrides,
});

const getYogaInstructionByPhase = (
  mode: BreathingMode,
  phaseId: BreathingPhaseId,
): LocalizedText => {
  if (mode === "box") {
    if (phaseId === "inhale") {
      return {
        en: "Sit straight and expand the chest gently.",
        hi: "रीढ़ सीधी रखें और छाती को धीरे से फैलाएं।",
      };
    }
    if (phaseId === "exhale") {
      return {
        en: "Relax shoulders and soften the jaw.",
        hi: "कंधों को ढीला छोड़ें और जबड़े को आराम दें।",
      };
    }
    return {
      en: "Stay stable and gently hold the breath.",
      hi: "स्थिर रहें और श्वास को सहज रूप से रोकें।",
    };
  }

  if (mode === "abdominal") {
    if (phaseId === "inhale") {
      return {
        en: "Expand the belly softly while inhaling.",
        hi: "श्वास लेते समय पेट को धीरे से फैलाएं।",
      };
    }
    if (phaseId === "exhale") {
      return {
        en: "Pull the belly inward while exhaling.",
        hi: "श्वास छोड़ते समय पेट को भीतर खींचें।",
      };
    }
    return {
      en: "Keep breath smooth and natural.",
      hi: "श्वास को सहज और लयबद्ध रखें।",
    };
  }

  if (phaseId === "chant_om") {
    return {
      en: "Focus on OM vibration and steady resonance.",
      hi: "ॐ की ध्वनि और कंपन पर ध्यान केंद्रित रखें।",
    };
  }

  if (phaseId === "inhale") {
    return {
      en: "Fill breath gently before OM chanting.",
      hi: "ॐ जप से पहले श्वास को धीरे से भरें।",
    };
  }

  return {
    en: "Sit in stillness and observe after-vibration.",
    hi: "स्थिर बैठकर जप के बाद की तरंगों को महसूस करें।",
  };
};

const localizeText = (text: LocalizedText, languageMode: LanguageMode): string => {
  if (languageMode === "en") return text.en;
  if (languageMode === "hi") return text.hi;
  return `${text.en} (${text.hi})`;
};

export const useBreathingEngine = () => {
  const [mode, setMode] = useState<BreathingMode>("box");
  const [durationSec, setDurationSec] = useState<number>(SESSION_DURATION_OPTIONS[1]);
  const [omDurationSec, setOmDurationSec] = useState<number>(getDefaultDurationForMode("box"));
  const [languageMode, setLanguageMode] = useState<LanguageMode>("en");
  const [state, setState] = useState<EngineState>(() =>
    createEngineState("box", SESSION_DURATION_OPTIONS[1], getDefaultDurationForMode("box")),
  );

  const phases = useMemo(() => getBreathingPattern(mode, omDurationSec), [mode, omDurationSec]);
  const currentPhase = phases[state.phaseIndex];
  const yoga = YOGA_GUIDANCE_BY_MODE[mode];
  const yogaInstruction = getYogaInstructionByPhase(mode, currentPhase.id);
  const isLocked = state.isRunning || state.isCountdown;
  const isImmersive = state.isRunning || state.isCountdown || state.showSessionComplete;

  const selectMode = useCallback(
    (nextMode: BreathingMode) => {
      if (isLocked) return;
      const nextOptions = getDurationOptionsForMode(nextMode);
      const nextPhaseDuration = nextOptions.includes(omDurationSec)
        ? omDurationSec
        : getDefaultDurationForMode(nextMode);
      setMode(nextMode);
      setOmDurationSec(nextPhaseDuration);
      setState(createEngineState(nextMode, durationSec, nextPhaseDuration));
    },
    [durationSec, omDurationSec, isLocked],
  );

  const selectDuration = useCallback(
    (seconds: number) => {
      if (isLocked) return;
      setDurationSec(seconds);
      setState(createEngineState(mode, seconds, omDurationSec));
    },
    [mode, omDurationSec, isLocked],
  );

  const selectOmDuration = useCallback(
    (seconds: number) => {
      if (isLocked) return;
      const allowed = getDurationOptionsForMode(mode);
      const normalized = allowed.includes(seconds) ? seconds : getDefaultDurationForMode(mode);
      setOmDurationSec(normalized);
      setState(createEngineState(mode, durationSec, normalized));
    },
    [mode, durationSec, isLocked],
  );

  const selectLanguageMode = useCallback((nextMode: LanguageMode) => {
    setLanguageMode(nextMode);
  }, []);

  const startSession = useCallback(() => {
    if (isLocked) return;
    setState(
      createEngineState(mode, durationSec, omDurationSec, {
        isCountdown: true,
        countdownLeft: PRE_START_COUNTDOWN_SECONDS,
      }),
    );
  }, [mode, durationSec, omDurationSec, isLocked]);

  const stopSession = useCallback(() => {
    setState((prev) => ({
      ...createEngineState(mode, durationSec, omDurationSec),
      sessionCompleteStep: prev.sessionCompleteStep,
    }));
  }, [mode, durationSec, omDurationSec]);

  const resetSession = useCallback(() => {
    setState((prev) => ({
      ...createEngineState(mode, durationSec, omDurationSec),
      sessionCompleteStep: prev.sessionCompleteStep,
    }));
  }, [mode, durationSec, omDurationSec]);

  useEffect(() => {
    if (!state.isCountdown) return;
    const timer = window.setInterval(() => {
      setState((prev) => {
        if (!prev.isCountdown) return prev;
        if (prev.countdownLeft <= 1) {
          return {
            ...prev,
            isCountdown: false,
            isRunning: true,
            countdownLeft: 0,
            phaseIndex: 0,
            phaseSecondsLeft: phases[0].seconds,
          };
        }
        return {
          ...prev,
          countdownLeft: prev.countdownLeft - 1,
        };
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [state.isCountdown, phases]);

  useEffect(() => {
    if (!state.isRunning) return;

    const timer = window.setInterval(() => {
      setState((prev) => {
        if (!prev.isRunning) return prev;

        if (prev.sessionSecondsLeft <= 1) {
          return {
            ...prev,
            isRunning: false,
            showSessionComplete: true,
            sessionSecondsLeft: 0,
            phaseSecondsLeft: SESSION_COMPLETE_HOLD_SECONDS,
            sessionCompleteStep: prev.sessionCompleteStep + 1,
          };
        }

        const nextSessionSeconds = prev.sessionSecondsLeft - 1;
        const shouldAdvance = prev.phaseSecondsLeft <= 1;
        const nextPhaseIndex = shouldAdvance ? (prev.phaseIndex + 1) % phases.length : prev.phaseIndex;
        const nextPhaseSecondsLeft = shouldAdvance
          ? phases[nextPhaseIndex].seconds
          : prev.phaseSecondsLeft - 1;

        return {
          ...prev,
          sessionSecondsLeft: nextSessionSeconds,
          phaseIndex: nextPhaseIndex,
          phaseSecondsLeft: nextPhaseSecondsLeft,
          phaseStep: shouldAdvance ? prev.phaseStep + 1 : prev.phaseStep,
        };
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [state.isRunning, phases]);

  useEffect(() => {
    if (!state.showSessionComplete) return;

    const timer = window.setTimeout(() => {
      setState((prev) => ({
        ...createEngineState(mode, durationSec, omDurationSec),
        sessionCompleteStep: prev.sessionCompleteStep,
      }));
    }, SESSION_COMPLETE_HOLD_SECONDS * 1000);

    return () => window.clearTimeout(timer);
  }, [state.showSessionComplete, mode, durationSec, omDurationSec]);

  const omSync = syncOmWithPhase(currentPhase.id, currentPhase.seconds);

  const phaseLabel = useMemo(() => {
    if (state.isCountdown) {
      return localizeText(
        {
          en: `Starting in ${state.countdownLeft}...`,
          hi: `${state.countdownLeft} सेकंड में शुरू...`,
        },
        languageMode,
      );
    }

    if (state.showSessionComplete) {
      return localizeText({ en: "Session Complete", hi: "सत्र पूर्ण" }, languageMode);
    }

    if (state.isRunning) {
      return localizeText(currentPhase.label, languageMode);
    }

    return localizeText({ en: "Ready", hi: "तैयार" }, languageMode);
  }, [
    state.isCountdown,
    state.countdownLeft,
    state.showSessionComplete,
    state.isRunning,
    currentPhase.label,
    languageMode,
  ]);

  return {
    mode,
    durationSec,
    omDurationSec,
    languageMode,
    languageOptions: LANGUAGE_OPTIONS,
    omDurationOptions: getDurationOptionsForMode(mode),
    durationOptions: SESSION_DURATION_OPTIONS,
    isRunning: state.isRunning,
    isCountdown: state.isCountdown,
    countdownLeft: state.countdownLeft,
    isLocked,
    isImmersive,
    showSessionComplete: state.showSessionComplete,
    sessionSecondsLeft: state.sessionSecondsLeft,
    phaseSecondsLeft: state.phaseSecondsLeft,
    phaseStep: state.phaseStep,
    phaseId: currentPhase.id,
    phaseDurationSec: currentPhase.seconds,
    phaseLabel,
    yogaName: localizeText(yoga.yogaName, languageMode),
    yogaInstruction: localizeText(yogaInstruction, languageMode),
    shouldPlayOm: state.isRunning && omSync.playOm,
    omPlaybackDurationSec: omSync.durationSec,
    sessionCompleteStep: state.sessionCompleteStep,
    selectMode,
    selectDuration,
    selectOmDuration,
    selectLanguageMode,
    startSession,
    stopSession,
    resetSession,
  };
};

export type BreathingEngine = ReturnType<typeof useBreathingEngine>;
