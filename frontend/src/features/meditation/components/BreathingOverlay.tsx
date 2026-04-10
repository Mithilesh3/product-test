import type { BreathingEngine } from "../hooks/useBreathingEngine";

import TimerDisplay from "./TimerDisplay";
import PhaseText from "./PhaseText";
import YogaGuide from "./YogaGuide";

interface BreathingOverlayProps {
  engine: BreathingEngine;
}

const localizeText = (languageMode: BreathingEngine["languageMode"], en: string, hi: string) => {
  if (languageMode === "en") return en;
  if (languageMode === "hi") return hi;
  return `${en} (${hi})`;
};

const getModeName = (engine: BreathingEngine) => {
  if (engine.mode === "box") {
    return localizeText(engine.languageMode, "Box Breathing", "चौकोर श्वसन");
  }

  if (engine.mode === "abdominal") {
    return localizeText(engine.languageMode, "Abdominal Breathing", "उदर श्वसन");
  }

  return localizeText(engine.languageMode, "OM Chanting", "ॐ जप");
};

const formatDuration = (seconds: number, languageMode: BreathingEngine["languageMode"]) => {
  if (languageMode === "hi") return `${Math.floor(seconds / 60)} मिनट`;
  if (languageMode === "both") return `${Math.floor(seconds / 60)} min (${Math.floor(seconds / 60)} मिनट)`;
  return `${Math.floor(seconds / 60)} min`;
};

const durationHeading = (engine: BreathingEngine) => {
  if (engine.mode === "om") {
    return localizeText(engine.languageMode, "OM Duration", "ॐ अवधि");
  }

  if (engine.mode === "box") {
    return localizeText(engine.languageMode, "Phase Duration", "चरण अवधि");
  }

  return localizeText(engine.languageMode, "Inhale Duration", "श्वास अवधि");
};

const showEnergyRising = (engine: BreathingEngine) =>
  engine.isRunning && (engine.phaseId === "exhale" || engine.phaseId === "chant_om");

export default function BreathingOverlay({ engine }: BreathingOverlayProps) {
  return (
    <div
      className={`breathing-overlay ${engine.isImmersive ? "immersive" : ""} ${engine.phaseId === "chant_om" ? "om-active" : ""}`}
    >
      <div
        className={`breathing-circle phase-${engine.phaseId}`}
        style={{ ["--phase-duration" as string]: `${Math.max(1, engine.phaseDurationSec)}s` }}
      >
        <TimerDisplay
          seconds={engine.isCountdown ? engine.countdownLeft : engine.phaseSecondsLeft}
          phaseId={engine.phaseId}
          phaseDurationSec={engine.phaseDurationSec}
        />
      </div>

      <div key={`phase-${engine.phaseStep}`} className="breathing-phase-block">
        <PhaseText phaseLabel={engine.phaseLabel} />
        {showEnergyRising(engine) ? (
          <p className="breathing-energy-label">
            {localizeText(engine.languageMode, "Energy Rising", "ऊर्जा ऊपर उठ रही है")}
          </p>
        ) : null}
        {!engine.isImmersive ? (
          <YogaGuide
            modeName={getModeName(engine)}
            yogaName={engine.yogaName}
            instruction={engine.yogaInstruction}
            languageMode={engine.languageMode}
          />
        ) : null}
      </div>

      {!engine.isImmersive ? (
        <div className="breathing-control-panel">
          <div className="breathing-om-duration-group">
            <p className="breathing-mini-heading">
              {localizeText(engine.languageMode, "Language", "भाषा")}
            </p>
            <div className="breathing-duration-group">
              {engine.languageOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`breathing-chip ${engine.languageMode === option.value ? "active" : ""}`}
                  onClick={() => engine.selectLanguageMode(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="breathing-om-duration-group">
            <p className="breathing-mini-heading">
              {durationHeading(engine)}
            </p>
            <div className="breathing-duration-group">
              {engine.omDurationOptions.map((value) => (
                <button
                  key={`om-${value}`}
                  type="button"
                  className={`breathing-chip ${engine.omDurationSec === value ? "active" : ""}`}
                  onClick={() => engine.selectOmDuration(value)}
                  disabled={engine.isLocked}
                >
                  {value}s
                </button>
              ))}
            </div>
          </div>

          <div className="breathing-duration-group">
            {engine.durationOptions.map((value) => (
              <button
                key={value}
                type="button"
                className={`breathing-chip ${engine.durationSec === value ? "active" : ""}`}
                onClick={() => engine.selectDuration(value)}
                disabled={engine.isLocked}
              >
                {formatDuration(value, engine.languageMode)}
              </button>
            ))}
          </div>

          <div className="breathing-action-group">
            <button
              type="button"
              className="breathing-action start"
              onClick={engine.startSession}
              disabled={engine.isLocked || engine.showSessionComplete}
            >
              {localizeText(engine.languageMode, "Start", "शुरू करें")}
            </button>
            <button
              type="button"
              className="breathing-action stop"
              onClick={engine.stopSession}
              disabled={!engine.isRunning && !engine.isCountdown}
            >
              {localizeText(engine.languageMode, "Stop", "रोकें")}
            </button>
            <button type="button" className="breathing-action reset" onClick={engine.resetSession}>
              {localizeText(engine.languageMode, "Reset", "रीसेट")}
            </button>
          </div>

          <p className="breathing-disclaimer">
            {localizeText(
              engine.languageMode,
              "Practice within your comfort. Do not strain your breath. Stop immediately if you feel discomfort. Consult a healthcare professional before practicing if you have respiratory, heart, or anxiety conditions.",
              "अपनी क्षमता के भीतर अभ्यास करें। श्वास पर जोर न डालें। असुविधा हो तो तुरंत रोकें। यदि आपको श्वसन, हृदय या चिंता संबंधी समस्या है, तो अभ्यास से पहले चिकित्सक से सलाह लें।",
            )}
          </p>
        </div>
      ) : null}
    </div>
  );
}
