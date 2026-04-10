import { useUsage } from "../../context/UsageContext";

export default function UsageProgress() {
  const { usage } = useUsage();
  if (!usage) return null;

  const percent =
    (usage.reports_used / usage.reports_limit) * 100;

  return (
    <div className="bg-gray-900 dark:bg-gray-800 p-6 rounded-xl">
      <p className="text-sm text-gray-400 mb-2">
        Usage: {usage.reports_used} / {usage.reports_limit}
      </p>
      <div className="w-full bg-gray-700 rounded h-3">
        <div
          className="bg-indigo-600 h-3 rounded"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}