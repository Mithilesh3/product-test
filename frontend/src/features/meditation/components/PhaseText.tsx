interface PhaseTextProps {
  phaseLabel: string;
}

export default function PhaseText({ phaseLabel }: PhaseTextProps) {
  return <div className="breathing-phase-text">{phaseLabel}</div>;
}
