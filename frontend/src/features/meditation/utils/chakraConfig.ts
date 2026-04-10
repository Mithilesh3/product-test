export type ChakraKey =
  | "root"
  | "sacral"
  | "solar"
  | "heart"
  | "throat"
  | "ajna"
  | "crown";

export interface ChakraPoint {
  key: ChakraKey;
  labelEn: string;
  labelHi: string;
  yPercent: number;
  color: string;
}

export const CHAKRA_POINTS: ChakraPoint[] = [
  {
    key: "root",
    labelEn: "Muladhara",
    labelHi: "मूलाधार",
    yPercent: 84,
    color: "rgba(248, 113, 113, 0.92)",
  },
  {
    key: "sacral",
    labelEn: "Svadhisthana",
    labelHi: "स्वाधिष्ठान",
    yPercent: 72,
    color: "rgba(251, 146, 60, 0.92)",
  },
  {
    key: "solar",
    labelEn: "Manipura",
    labelHi: "मणिपुर",
    yPercent: 60,
    color: "rgba(250, 204, 21, 0.93)",
  },
  {
    key: "heart",
    labelEn: "Anahata",
    labelHi: "अनाहत",
    yPercent: 48,
    color: "rgba(110, 231, 183, 0.95)",
  },
  {
    key: "throat",
    labelEn: "Vishuddha",
    labelHi: "विशुद्ध",
    yPercent: 38,
    color: "rgba(125, 211, 252, 0.95)",
  },
  {
    key: "ajna",
    labelEn: "Ajna",
    labelHi: "आज्ञा",
    yPercent: 26,
    color: "rgba(196, 181, 253, 0.96)",
  },
  {
    key: "crown",
    labelEn: "Sahasrara",
    labelHi: "सहस्रार",
    yPercent: 14,
    color: "rgba(250, 204, 21, 0.9)",
  },
];

const lerp = (from: number, to: number, t: number) => from + (to - from) * t;

export const resolveActiveChakra = (progress: number): ChakraKey => {
  if (progress < 0.4) return "heart";
  if (progress < 0.7) return "throat";
  if (progress < 0.95) return "ajna";
  return "crown";
};

export const resolveChakraY = (progress: number): number => {
  const p = Math.max(0, Math.min(1, progress));

  if (p < 0.4) {
    return lerp(48, 38, p / 0.4);
  }

  if (p < 0.7) {
    return lerp(38, 26, (p - 0.4) / 0.3);
  }

  return lerp(26, 14, (p - 0.7) / 0.3);
};
