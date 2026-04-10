import type { ReportStepProps } from "../../../types/reportForm";

export default function StepEmotional({
  formData,
  setFormData,
  next,
  prev,
}: ReportStepProps) {
  const update = (field: string, value: number) => {
    setFormData((prevData) => ({
      ...prevData,
      emotional: {
        ...prevData.emotional,
        [field]: value,
      },
    }));
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Emotional State</h2>

      <input
        type="number"
        min={1}
        max={10}
        placeholder="Anxiety Level (1-10)"
        className="input"
        value={formData.emotional?.anxiety_level || ""}
        onChange={(e) => update("anxiety_level", Number(e.target.value || 1))}
      />

      <input
        type="number"
        min={1}
        max={10}
        placeholder="Decision Confusion (1-10)"
        className="input"
        value={formData.emotional?.decision_confusion || ""}
        onChange={(e) => update("decision_confusion", Number(e.target.value || 1))}
      />

      <input
        type="number"
        min={1}
        max={10}
        placeholder="Impulse Control (1-10)"
        className="input"
        value={formData.emotional?.impulse_control || ""}
        onChange={(e) => update("impulse_control", Number(e.target.value || 1))}
      />

      <input
        type="number"
        min={1}
        max={10}
        placeholder="Emotional Stability (1-10)"
        className="input"
        value={formData.emotional?.emotional_stability || ""}
        onChange={(e) => update("emotional_stability", Number(e.target.value || 1))}
      />

      <div className="flex justify-between">
        <button onClick={prev} className="btn-secondary">Back</button>
        <button onClick={next} className="btn-primary">Continue</button>
      </div>
    </div>
  );
}
