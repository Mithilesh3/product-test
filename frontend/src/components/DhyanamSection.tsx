import { useEffect, useRef } from "react";
import "../styles/Dhyanamsection.css";
import BreathingOverlay from "../features/meditation/components/BreathingOverlay";
import ChakraFlow from "../features/meditation/components/ChakraFlow";
import { useBreathingEngine } from "../features/meditation/hooks/useBreathingEngine";
import { useChakraFlow } from "../features/meditation/hooks/useChakraFlow";
import { BREATHING_PRESETS, type BreathingMode, type LanguageMode } from "../features/meditation/utils/breathingPatterns";

type BrowserAudioContext = typeof AudioContext;

interface OmPlaybackState {
  source: AudioBufferSourceNode;
  gain: GainNode;
}

const getAudioContext = (): BrowserAudioContext | undefined =>
  window.AudioContext || (window as unknown as { webkitAudioContext?: BrowserAudioContext }).webkitAudioContext;

const localizeText = (languageMode: LanguageMode, en: string, hi: string) => {
  if (languageMode === "en") return en;
  if (languageMode === "hi") return hi;
  return `${en} (${hi})`;
};

const modeCopy = (mode: BreathingMode, languageMode: LanguageMode, omDurationSec: number) => {
  if (mode === "box") {
    return {
      title: localizeText(languageMode, "Box Breathing", "चौकोर श्वसन"),
      subtitle: localizeText(
        languageMode,
        `${omDurationSec}s inhale | ${omDurationSec}s hold | ${omDurationSec}s exhale | ${omDurationSec}s hold`,
        `${omDurationSec}से श्वास | ${omDurationSec}से रोकें | ${omDurationSec}से छोड़ें | ${omDurationSec}से रोकें`,
      ),
    };
  }

  if (mode === "abdominal") {
    const exhale = omDurationSec + 2;
    return {
      title: localizeText(languageMode, "Abdominal Breathing", "उदर श्वसन"),
      subtitle: localizeText(
        languageMode,
        `${omDurationSec}s inhale | ${exhale}s exhale`,
        `${omDurationSec}से श्वास | ${exhale}से छोड़ें`,
      ),
    };
  }

  return {
    title: localizeText(languageMode, "OM Chanting", "ॐ जप"),
    subtitle: localizeText(
      languageMode,
      `4s inhale | ${omDurationSec}s OM | 2s silence`,
      `4से श्वास | ${omDurationSec}से ॐ | 2से मौन`,
    ),
  };
};

export default function DhyanamSection() {
  const audioCtxRef = useRef<AudioContext | null>(null);
  const omBufferRef = useRef<AudioBuffer | null>(null);
  const omLoadPromiseRef = useRef<Promise<AudioBuffer | null> | null>(null);
  const omPlaybackRef = useRef<OmPlaybackState | null>(null);
  const stopTimeoutRef = useRef<number | null>(null);

  const breathing = useBreathingEngine();
  const chakraFlow = useChakraFlow({
    isRunning: breathing.isRunning,
    phaseId: breathing.phaseId,
    phaseDurationSec: breathing.phaseDurationSec,
    phaseStep: breathing.phaseStep,
  });

  const clearOmTimers = () => {
    if (stopTimeoutRef.current) {
      window.clearTimeout(stopTimeoutRef.current);
      stopTimeoutRef.current = null;
    }
  };

  const teardownOmPlayback = () => {
    const playback = omPlaybackRef.current;
    if (!playback) return;

    try {
      playback.source.stop();
    } catch {
      // no-op
    }

    try {
      playback.source.disconnect();
    } catch {
      // no-op
    }

    try {
      playback.gain.disconnect();
    } catch {
      // no-op
    }

    omPlaybackRef.current = null;
  };

  const stopOmImmediately = () => {
    clearOmTimers();
    teardownOmPlayback();
  };

  const getOrCreateAudioContext = async () => {
    const Ctx = getAudioContext();
    if (!Ctx) return null;

    if (!audioCtxRef.current) {
      audioCtxRef.current = new Ctx();
    }

    if (audioCtxRef.current.state === "suspended") {
      await audioCtxRef.current.resume();
    }

    return audioCtxRef.current;
  };

  const loadOmBuffer = async (ctx: AudioContext): Promise<AudioBuffer | null> => {
    if (omBufferRef.current) return omBufferRef.current;

    if (!omLoadPromiseRef.current) {
      const loadFromSource = async (sourcePath: string) => {
        const res = await fetch(sourcePath);
        if (!res.ok) return null;
        const ab = await res.arrayBuffer();
        return ctx.decodeAudioData(ab.slice(0));
      };

      omLoadPromiseRef.current = (async () => {
        const primary = await loadFromSource("/om15s.mpeg");
        if (primary) {
          omBufferRef.current = primary;
          return primary;
        }

        const fallback = await loadFromSource("/Om.mp4");
        if (fallback) {
          omBufferRef.current = fallback;
          return fallback;
        }

        return null;
      })()
        .finally(() => {
          omLoadPromiseRef.current = null;
        });
    }

    return omLoadPromiseRef.current;
  };

  const playOmForDuration = async (durationSec: number) => {
    const ctx = await getOrCreateAudioContext();
    if (!ctx) return;

    const buffer = await loadOmBuffer(ctx);
    if (!buffer) return;

    stopOmImmediately();

    const totalSec = Math.max(1, durationSec);
    const now = ctx.currentTime + 0.01;
    const endAt = now + totalSec;

    const source = ctx.createBufferSource();
    source.buffer = buffer;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.linearRampToValueAtTime(0.95, now + 0.16);
    gain.gain.setValueAtTime(0.95, Math.max(now + 0.16, endAt - 0.22));
    gain.gain.linearRampToValueAtTime(0.0001, endAt);
    source.playbackRate.setValueAtTime(1, now);

    source.connect(gain);
    gain.connect(ctx.destination);

    if (totalSec <= buffer.duration) {
      source.loop = false;
      source.start(now, 0, totalSec);
    } else {
      source.loop = true;
      source.start(now, 0);
    }
    source.stop(endAt + 0.02);

    omPlaybackRef.current = { source, gain };

    source.onended = () => {
      if (omPlaybackRef.current?.source === source) {
        teardownOmPlayback();
      }
    };

    stopTimeoutRef.current = window.setTimeout(() => {
      if (omPlaybackRef.current?.source === source) {
        teardownOmPlayback();
      }
    }, totalSec * 1000 + 120);
  };

  const playSoftBell = () => {
    const Ctx = getAudioContext();
    if (!Ctx) return;

    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(523.25, ctx.currentTime);
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.04);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 1.2);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 1.25);
    window.setTimeout(() => void ctx.close(), 1400);
  };

  useEffect(() => {
    if (!breathing.isRunning) {
      stopOmImmediately();
      return;
    }

    if (breathing.shouldPlayOm) {
      void playOmForDuration(breathing.omPlaybackDurationSec);
      return;
    }

    stopOmImmediately();
  }, [breathing.phaseStep, breathing.shouldPlayOm, breathing.omPlaybackDurationSec, breathing.isRunning]);

  useEffect(() => {
    if (breathing.sessionCompleteStep <= 0) return;
    stopOmImmediately();
    playSoftBell();
  }, [breathing.sessionCompleteStep]);

  useEffect(
    () => () => {
      stopOmImmediately();
      if (audioCtxRef.current) {
        void audioCtxRef.current.close();
        audioCtxRef.current = null;
      }
    },
    [],
  );

  useEffect(() => {
    const unlockAudio = () => {
      void getOrCreateAudioContext();
    };
    window.addEventListener("pointerdown", unlockAudio, { once: true });
    return () => window.removeEventListener("pointerdown", unlockAudio);
  }, []);

  const activateMode = (mode: BreathingMode) => {
    if (breathing.isLocked) return;
    breathing.selectMode(mode);
  };

  return (
    <section className="dhyanam-section">
      <div className="dhyanam-bg">
        <video autoPlay muted loop playsInline>
          <source src="/Seven Chakras.mp4" type="video/mp4" />
        </video>
      </div>

      {breathing.isRunning && breathing.mode === "om" && breathing.phaseId === "chant_om" ? (
        <div
          className="om-particles"
          style={{ ["--om-intensity" as string]: String(chakraFlow.omIntensity) }}
          aria-hidden="true"
        >
          {Array.from({ length: 8 }).map((_, idx) => (
            <span key={idx} className="om-particle">ॐ</span>
          ))}
        </div>
      ) : null}

      <ChakraFlow
        isActive={chakraFlow.isActive}
        activeChakra={chakraFlow.activeChakra}
        energyY={chakraFlow.energyY}
        omIntensity={chakraFlow.omIntensity}
        languageMode={breathing.languageMode}
      />

      <div className={`dhyanam-container ${breathing.isImmersive ? "is-immersive" : ""}`}>
        <div className={`dhyanam-left ${breathing.isImmersive ? "immersive-hidden" : ""}`}>
          <h2>
            {localizeText(breathing.languageMode, "Enter the State of", "ध्यानम की अवस्था में")} <br />
            {localizeText(breathing.languageMode, "Dhyanam", "प्रवेश करें")}
          </h2>

          <p className="dhyanam-quote">
            {localizeText(
              breathing.languageMode,
              '"Silence is not empty. It is full of answers."',
              '"मौन खाली नहीं है, यह उत्तरों से भरा है।"',
            )}
          </p>
          <p>
            {localizeText(
              breathing.languageMode,
              "Align your mind, body, and energy with the cosmic vibrations.",
              "अपने मन, शरीर और ऊर्जा को ब्रह्मांडीय कंपन के साथ संतुलित करें।",
            )}
          </p>
          <p className="dhyanam-breath">
            {localizeText(breathing.languageMode, "Inhale | Hold | Exhale", "श्वास लें | रोकें | छोड़ें")}
          </p>
          <p className="dhyanam-hint">
            {localizeText(
              breathing.languageMode,
              "Use the panel controls to start, stop, and reset your practice.",
              "अभ्यास शुरू, रोकने और रीसेट करने के लिए पैनल नियंत्रण का उपयोग करें।",
            )}
          </p>
        </div>

        <div className="dhyanam-center">
          <BreathingOverlay engine={breathing} />
        </div>

        <div className={`dhyanam-right ${breathing.isImmersive ? "immersive-hidden" : ""}`}>
          <p className="dhyanam-right-heading">
            {localizeText(breathing.languageMode, "Guided Practice Modes", "मार्गदर्शित अभ्यास मोड")}
          </p>
          {BREATHING_PRESETS.map((preset) => {
            const copy = modeCopy(preset.mode, breathing.languageMode, breathing.omDurationSec);
            return (
              <button
                key={preset.mode}
                type="button"
                className={`dhyanam-mode-btn ${breathing.mode === preset.mode ? "active" : ""}`}
                onClick={() => activateMode(preset.mode)}
                disabled={breathing.isLocked}
              >
                <span className="dhyanam-mode-title">{copy.title}</span>
                <span className="dhyanam-mode-subtitle">{copy.subtitle}</span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
