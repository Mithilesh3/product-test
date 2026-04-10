import { useEffect, useMemo, useRef, useState } from "react";
import { resolveActiveChakra, resolveChakraY, type ChakraKey } from "../utils/chakraConfig";
import type { BreathingPhaseId } from "../utils/breathingPatterns";

interface ChakraFlowInput {
  isRunning: boolean;
  phaseId: BreathingPhaseId;
  phaseDurationSec: number;
  phaseStep: number;
}

interface ChakraFlowState {
  isActive: boolean;
  progress: number;
  activeChakra: ChakraKey;
  energyY: number;
  omIntensity: number;
}

const clamp = (value: number, min = 0, max = 1) => Math.max(min, Math.min(max, value));

const isRisingPhase = (phaseId: BreathingPhaseId) => phaseId === "exhale" || phaseId === "chant_om";

export const useChakraFlow = ({
  isRunning,
  phaseId,
  phaseDurationSec,
  phaseStep,
}: ChakraFlowInput): ChakraFlowState => {
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);

  const active = isRunning && isRisingPhase(phaseId);

  useEffect(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }

    if (!active) {
      setProgress(0);
      return;
    }

    const durationMs = Math.max(300, phaseDurationSec * 1000);
    const start = performance.now();

    const tick = (now: number) => {
      const nextProgress = clamp((now - start) / durationMs);
      setProgress(nextProgress);

      if (nextProgress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [active, phaseDurationSec, phaseStep]);

  const activeChakra = useMemo(() => resolveActiveChakra(progress), [progress]);
  const energyY = useMemo(() => resolveChakraY(progress), [progress]);

  const omIntensity = useMemo(() => {
    if (!active) return 0;
    // Peak near middle and sustain slightly towards the end.
    const arch = 1 - Math.abs(progress - 0.5) * 1.6;
    return clamp(0.35 + arch * 0.65, 0.35, 1);
  }, [active, progress]);

  return {
    isActive: active,
    progress,
    activeChakra,
    energyY,
    omIntensity,
  };
};
