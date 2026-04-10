import type {
  ReportStepProps,
  RiskToleranceValue,
} from "../../../types/reportForm";

export default function StepFinancial({
  formData,
  setFormData,
  next,
  prev,
}: ReportStepProps) {
  const update = (field: string, value: string | number) => {
    setFormData((prevData) => ({
      ...prevData,
      financial: {
        ...prevData.financial,
        [field]: value,
      },
    }));
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Financial Snapshot</h2>

      <input
        type="number"
        placeholder="Monthly Income"
        className="input"
        value={formData.financial?.monthly_income || ""}
        onChange={(e) => update("monthly_income", Number(e.target.value || 0))}
      />

      <input
        type="number"
        min={0}
        max={100}
        placeholder="Savings Ratio (%)"
        className="input"
        value={formData.financial?.savings_ratio || ""}
        onChange={(e) => update("savings_ratio", Number(e.target.value || 0))}
      />

      <input
        type="number"
        min={0}
        max={100}
        placeholder="Debt Ratio (%)"
        className="input"
        value={formData.financial?.debt_ratio || ""}
        onChange={(e) => update("debt_ratio", Number(e.target.value || 0))}
      />

      <select
        className="input"
        value={formData.financial?.risk_tolerance || ""}
        onChange={(e) =>
          update("risk_tolerance", e.target.value as RiskToleranceValue)
        }
      >
        <option value="">Risk Tolerance</option>
        <option value="low">Low</option>
        <option value="moderate">Moderate</option>
        <option value="high">High</option>
      </select>

      <div className="flex justify-between">
        <button onClick={prev} className="btn-secondary">Back</button>
        <button onClick={next} className="btn-primary">Continue</button>
      </div>
    </div>
  );
}
