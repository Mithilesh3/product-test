import { CHAKRA_POINTS } from "../utils/chakraConfig";
import type { LanguageMode } from "../utils/breathingPatterns";
import type { ChakraKey } from "../utils/chakraConfig";

interface ChakraFlowProps {
  isActive: boolean;
  activeChakra: ChakraKey;
  energyY: number;
  omIntensity: number;
  languageMode: LanguageMode;
}

const localize = (language: LanguageMode, en: string, hi: string) => {
  if (language === "en") return en;
  if (language === "hi") return hi;
  return `${en} (${hi})`;
};

export default function ChakraFlow({
  isActive,
  activeChakra,
  energyY,
  omIntensity,
  languageMode,
}: ChakraFlowProps) {
  if (!isActive) return null;

  const activePoint = CHAKRA_POINTS.find((point) => point.key === activeChakra) ?? CHAKRA_POINTS[0];

  return (
    <div
      className="chakra-flow"
      style={{
        ["--chakra-intensity" as string]: String(omIntensity),
        ["--chakra-energy-y" as string]: `${energyY}%`,
        ["--chakra-pulse-ms" as string]: `${Math.max(700, Math.round(1500 - omIntensity * 650))}ms`,
      }}
      aria-hidden="true"
    >
      <div className="chakra-flow-column">
        <div className="chakra-flow-line" />
        {CHAKRA_POINTS.map((point) => (
          <div
            key={point.key}
            className={`chakra-flow-node ${point.key === activeChakra ? "active" : ""}`}
            style={{
              ["--chakra-node-y" as string]: `${point.yPercent}%`,
              ["--chakra-color" as string]: point.color,
            }}
          />
        ))}
        <div
          className="chakra-flow-energy"
          style={{
            ["--chakra-color" as string]: activePoint.color,
          }}
        />
      </div>
      <div className="chakra-flow-caption">
        {localize(languageMode, activePoint.labelEn, activePoint.labelHi)}
      </div>
    </div>
  );
}
