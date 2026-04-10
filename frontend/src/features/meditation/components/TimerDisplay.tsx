interface TimerDisplayProps {
  seconds: number;
  phaseId: string;
  phaseDurationSec: number;
}

export default function TimerDisplay({ seconds, phaseId, phaseDurationSec }: TimerDisplayProps) {
  return (
    <div
      className={`breathing-timer phase-${phaseId}`}
      style={{ ["--phase-duration" as string]: `${Math.max(1, phaseDurationSec)}s` }}
      aria-live="polite"
      aria-label={`Timer ${seconds} seconds`}
    >
      {seconds}
    </div>
  );
}
