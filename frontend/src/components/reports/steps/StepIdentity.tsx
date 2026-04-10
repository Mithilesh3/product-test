import type { ReportStepProps } from "../../../types/reportForm";

export default function StepIdentity({
  formData,
  setFormData,
  next,
}: ReportStepProps) {
  const update = (field: string, value: string) => {
    setFormData((prevData) => ({
      ...prevData,
      identity: {
        ...prevData.identity,
        [field]: value,
      },
    }));
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Identity Details</h2>

      <input
        placeholder="Full Name"
        className="input"
        value={formData.identity?.full_name || ""}
        onChange={(e) => update("full_name", e.target.value)}
      />

      <input
        placeholder="Gender"
        className="input"
        value={formData.identity?.gender || ""}
        onChange={(e) => update("gender", e.target.value)}
      />

      <input
        type="email"
        placeholder="Email"
        className="input"
        value={formData.identity?.email || ""}
        onChange={(e) => update("email", e.target.value)}
      />

      <input
        placeholder="Mobile Number"
        className="input"
        value={formData.identity?.mobile_number || ""}
        onChange={(e) => update("mobile_number", e.target.value)}
      />

      <button onClick={next} className="btn-primary">
        Continue
      </button>
    </div>
  );
}
