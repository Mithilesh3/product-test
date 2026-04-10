import type { ReportStepProps } from "../../../types/reportForm";

export default function StepHealth({ next, prev }: ReportStepProps) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-6">Health Profile</h2>
      <div className="flex justify-between">
        <button onClick={prev} className="btn-secondary">Back</button>
        <button onClick={next} className="btn-primary">Continue</button>
      </div>
    </div>
  );
}
