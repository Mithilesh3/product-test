import type { ReportStepProps } from "../../../types/reportForm";

export default function StepFocus({
  formData,
  setFormData,
  next,
  prev,
}: ReportStepProps) {
  const updateProblem = (value: string) => {
    setFormData((prevData) => ({
      ...prevData,
      focus: { life_focus: "general_alignment" },
      current_problem: value,
    }));
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Current Problem</h2>

      <textarea
        className="input min-h-28"
        placeholder="Describe your current issue (e.g. Debt and Loans)"
        value={formData.current_problem || ""}
        onChange={(e) => updateProblem(e.target.value)}
      />

      <div className="flex justify-between">
        <button onClick={prev} className="btn-secondary">Back</button>
        <button onClick={next} className="btn-primary">Continue</button>
      </div>
    </div>
  );
}
