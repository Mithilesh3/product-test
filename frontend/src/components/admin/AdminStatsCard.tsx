export default function AdminStatsCard({ label, value }: any) {
  return (
    <div className="bg-gray-900 p-6 rounded-xl">
      <p className="text-gray-400 text-sm">{label}</p>
      <p className="text-3xl font-bold">{value}</p>
    </div>
  );
}