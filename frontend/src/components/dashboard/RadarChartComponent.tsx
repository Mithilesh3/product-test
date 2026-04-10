import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface RadarDataItem {
  metric: string;
  score: number;
}

interface Props {
  data: RadarDataItem[];
}

export default function RadarChartComponent({ data }: Props) {
  return (
    <div className="bg-gray-900 p-6 rounded-xl shadow-md">
      <h2 className="text-xl font-semibold mb-6">Intelligence Radar</h2>

      <ResponsiveContainer width="100%" height={400}>
        <RadarChart data={data}>
          <PolarGrid stroke="#444" />
          <PolarAngleAxis dataKey="metric" stroke="#ccc" />
          <PolarRadiusAxis stroke="#888" domain={[0, 100]} />
          <Tooltip />

          <Radar
            name="Score"
            dataKey="score"
            stroke="#6366F1"
            fill="#6366F1"
            fillOpacity={0.6}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
