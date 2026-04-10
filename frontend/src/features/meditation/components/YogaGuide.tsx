import type { LanguageMode } from "../utils/breathingPatterns";

interface YogaGuideProps {
  modeName: string;
  yogaName: string;
  instruction: string;
  languageMode: LanguageMode;
}

const resolveLabels = (languageMode: LanguageMode) => {
  if (languageMode === "en") {
    return {
      mode: "Mode",
      yoga: "Yoga",
      instruction: "Instruction",
    };
  }

  if (languageMode === "hi") {
    return {
      mode: "अभ्यास",
      yoga: "योग",
      instruction: "निर्देश",
    };
  }

  return {
    mode: "Mode (अभ्यास)",
    yoga: "Yoga (योग)",
    instruction: "Instruction (निर्देश)",
  };
};

export default function YogaGuide({ modeName, yogaName, instruction, languageMode }: YogaGuideProps) {
  const labels = resolveLabels(languageMode);

  return (
    <div className="breathing-yoga-guide">
      <p className="breathing-yoga-mode">{labels.mode}: {modeName}</p>
      <p className="breathing-yoga-title">{labels.yoga}: {yogaName}</p>
      <p className="breathing-yoga-instruction">{labels.instruction}: {instruction}</p>
    </div>
  );
}
