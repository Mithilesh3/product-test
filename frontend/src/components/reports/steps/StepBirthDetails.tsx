import type { ReportStepProps } from "../../../types/reportForm";

export default function StepBirthDetails({
  formData,
  setFormData,
  next,
  prev,
}: ReportStepProps) {
  const update = (field: string, value: string) => {
    setFormData((prevData) => ({
      ...prevData,
      birth_details: {
        ...prevData.birth_details,
        [field]: value,
      },
    }));
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Birth Details</h2>

      <input
        type="date"
        className="input"
        value={formData.birth_details?.date_of_birth || ""}
        onChange={(e) => update("date_of_birth", e.target.value)}
      />

      <input
        placeholder="Birth Place (City, State)"
        className="input"
        value={formData.birth_details?.birthplace_city || ""}
        onChange={(e) => update("birthplace_city", e.target.value)}
      />

      <div className="flex justify-between">
        <button onClick={prev} className="btn-secondary">
          Back
        </button>
        <button onClick={next} className="btn-primary">
          Continue
        </button>
      </div>
    </div>
  );
}
