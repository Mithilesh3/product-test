import { type ReactNode } from "react";

import type { HindiSection, ReportResponse } from "../../types/report";
import {
  FooterSummaryRibbon,
  HighlightValueBlock,
  InsightTextPanel,
  KeyValueList,
  MainContentCard,
  ReportPageBackground,
  SectionHeader,
  renderSectionPage,
  type ReportTemplateThemeConfig,
  type ReportSectionTemplateData,
  type SectionTemplateType,
  type SectionVisualType,
} from "./SectionPageTemplate";

export type PrintableSectionKey =
  | "cover"
  | "mobileEnergy"
  | "loShuGrid"
  | "mobileEffects"
  | "lifePathContext"
  | "keyLifeAreas"
  | "recommendation"
  | "suggestedNumbers"
  | "charging"
  | "remedies"
  | "tracker21Days"
  | "summary"
  | "keyInsight"
  | "nextSteps"
  | "upgrade";

const PRINTABLE_SECTIONS: PrintableSectionKey[] = [
  "cover",
  "mobileEnergy",
  "loShuGrid",
  "mobileEffects",
  "lifePathContext",
  "keyLifeAreas",
  "recommendation",
  "suggestedNumbers",
  "charging",
  "remedies",
  "tracker21Days",
  "summary",
  "keyInsight",
  "nextSteps",
  "upgrade",
];

const CUSTOM_TEMPLATE_THEME: ReportTemplateThemeConfig = {
  backgroundTop: "#FFF8E7",
  backgroundMid: "#FFF3C4",
  backgroundBottom: "#FFE9A8",
  primaryText: "#4A3419",
  secondaryText: "#7A5A2B",
  accentGold: "#D4A437",
  cardBackground: "rgba(255,255,255,0.72)",
  cardBorder: "rgba(212,164,55,0.35)",
};

const RAW_DEBUG_KEYS = new Set([
  "POINT_1",
  "POINT_2",
  "VERDICT_BOX",
  "CHARGING_ROW",
  "REMEDY_SP_ROW",
  "REMEDY_DIGITAL_ROW",
  "TRACKER_ROW",
  "NEXTSTEP_ROW",
  "SUGGESTED_OPTION",
  "SUMMARY_ROW",
  "KEY_INSIGHT",
  "CTA_TEXT",
]);

const PRINT_PAGE_META: Record<
  Exclude<PrintableSectionKey, "cover">,
  {
    title: string;
    subtitle: string;
    type: SectionTemplateType;
    tag: string;
    visualType: SectionVisualType;
    matchers: string[];
  }
> = {
  mobileEnergy: {
    title: "मोबाइल नंबर ऊर्जा | Mobile Number Energy",
    subtitle: "मूल अंक, ग्रह, तत्व और ऊर्जा संकेत | Core vibration, planet, element, and energy signature",
    type: "insight",
    tag: "अवलोकन | Overview",
    visualType: "none",
    matchers: ["mobile", "energy", "vibration"],
  },
  loShuGrid: {
    title: "लो शू ग्रिड विश्लेषण | Lo Shu Grid Analysis",
    subtitle: "अंक आवृत्ति, मौजूद/अनुपस्थित अंक और छिपा पैटर्न | Digit frequency, present/missing digits, and hidden pattern",
    type: "visual",
    tag: "ऊर्जा पैटर्न | Energy Pattern",
    visualType: "matrix",
    matchers: ["lo shu", "loshu", "grid", "missing", "repeating"],
  },
  mobileEffects: {
    title: "मोबाइल नंबर प्रभाव | Mobile Number Effects",
    subtitle: "सकारात्मक प्रभाव और संभावित चुनौती पैटर्न | Positive influence and possible challenge pattern",
    type: "analysis",
    tag: "विश्लेषण | Analysis",
    visualType: "none",
    matchers: ["effect", "impact", "positive", "challenge"],
  },
  lifePathContext: {
    title: "जीवन पथ संदर्भ | Life Path Context",
    subtitle: "मोबाइल कंपन और जीवन पथ ऊर्जा का तालमेल | Alignment between mobile vibration and life path energy",
    type: "insight",
    tag: "मुख्य अंतर्दृष्टि | Core Insight",
    visualType: "none",
    matchers: ["life path", "compatibility", "alignment"],
  },
  keyLifeAreas: {
    title: "प्रमुख जीवन क्षेत्रों पर प्रभाव | Impact on Key Life Areas",
    subtitle: "निरंतरता, आत्मविश्वास, वित्त, निष्पादन, निर्णय",
    type: "grid",
    tag: "विश्लेषण | Analysis",
    visualType: "none",
    matchers: ["life areas", "consistency", "confidence", "financial", "career"],
  },
  recommendation: {
    title: "मोबाइल नंबर सिफारिश | Mobile Recommendation",
    subtitle: "रखें, संभालें या बदलें — कारण सहित | Keep, manage, or change with focused reasoning",
    type: "summary",
    tag: "सिफारिश | Recommendation",
    visualType: "none",
    matchers: ["recommendation", "verdict", "keep", "change", "manage"],
  },
  suggestedNumbers: {
    title: "सुझाए गए मोबाइल नंबर | Suggested Mobile Numbers",
    subtitle: "3 विकल्प, vibration, key digits और reasoning",
    type: "grid",
    tag: "विकल्प | Options",
    visualType: "none",
    matchers: ["suggested", "option", "number structure", "if changing"],
  },
  charging: {
    title: "मोबाइल चार्जिंग दिशा | Charging Direction Protocol",
    subtitle: "दिशा, दिन, समय और विधि | Direction, day, timing, and ritual method",
    type: "insight",
    tag: "अनुष्ठान | Ritual",
    visualType: "icon",
    matchers: ["charging", "direction", "best time", "ritual"],
  },
  remedies: {
    title: "उपाय | Remedies for Your Current Number",
    subtitle: "आध्यात्मिक, भौतिक, डिजिटल और दृश्य संतुलन क्रियाएँ",
    type: "analysis",
    tag: "उपाय | Remedies",
    visualType: "none",
    matchers: ["remedy", "mantra", "digital", "visual", "rudraksha"],
  },
  tracker21Days: {
    title: "21-Day Remedy Tracker",
    subtitle: "Week-by-week implementation and completion rhythm",
    type: "grid",
    tag: "Tracker",
    visualType: "none",
    matchers: ["21-day", "tracker", "week 1", "week 2", "week 3"],
  },
  summary: {
    title: "सारांश | Summary",
    subtitle: "वर्तमान स्थिति बनाम सुझावित कार्रवाई | Current vs recommended snapshot",
    type: "summary",
    tag: "सारांश | Summary",
    visualType: "none",
    matchers: ["summary", "status", "current", "recommendation"],
  },
  keyInsight: {
    title: "मुख्य अंतर्दृष्टि | Your Key Insight",
    subtitle: "एक शक्तिशाली सार जो आपकी मुख्य दिशा स्पष्ट करे | One decisive message for focused execution",
    type: "summary",
    tag: "मुख्य अंतर्दृष्टि | Core Insight",
    visualType: "none",
    matchers: ["key insight", "core insight", "main insight"],
  },
  nextSteps: {
    title: "अगले कदम | Next Steps",
    subtitle: "तुरंत लागू करने योग्य कार्य योजना | Immediate execution plan with prioritized actions",
    type: "grid",
    tag: "कार्रवाई | Action",
    visualType: "none",
    matchers: ["next steps", "action", "plan", "start now"],
  },
  upgrade: {
    title: "समापन संदेश | Closing & Upgrade Path",
    subtitle: "धन्यवाद संदेश, अगली दिशा और प्रीमियम विकल्प | Thank-you note, direction, and premium options",
    type: "summary",
    tag: "धन्यवाद | Thank You",
    visualType: "none",
    matchers: ["upgrade", "standard", "enterprise", "cta"],
  },
};

type ParsedLine = { label: string; value: string };

function sanitizeText(value: string) {
  return repairDisplayText(String(value || ""))
    .replace(/\*\*/g, "")
    .replace(/\|{1,}/g, " ")
    .replace(/[Â¦â€–]+/g, " ")
    .replace(/[\u{1F300}-\u{1FAFF}\u2600-\u27BF]/gu, "")
    .replace(/(?:âœ…|âš ï¸|âŒ|ï¸)/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function enforceIndiaMobilePatternStart(pattern: string, optionIndex = 0): string {
  const cleaned = sanitizeText(String(pattern || ""));
  if (!cleaned) return cleaned;
  const preferredStarts = ["9", "8", "7"];
  const fallbackStart = preferredStarts[Math.max(0, Math.min(optionIndex, preferredStarts.length - 1))] || "9";

  const tokenMatch = cleaned.match(/^\s*\[(\d)\]/);
  if (tokenMatch) {
    const current = tokenMatch[1];
    if (["6", "7", "8", "9"].includes(current)) return cleaned;
    return cleaned.replace(/^\s*\[(\d)\]/, `[${fallbackStart}]`);
  }

  const fullNumberMatch = cleaned.match(/^\s*(\d)/);
  if (fullNumberMatch) {
    const current = fullNumberMatch[1];
    if (["6", "7", "8", "9"].includes(current)) return cleaned;
    return cleaned.replace(/^\s*\d/, fallbackStart);
  }

  return cleaned;
}

const MOJIBAKE_MARKER =
  /(Ã|Â|à¤|à¥|ï¿½|â€™|â€œ|â€|â€“|â€”|Ãƒ|Ã‚|Ã Â¤|Ã¯Â¿Â½|Ã¢â‚¬|ðŸ|ð|Ã°|âœ|âš|â|â|â)/;

function countMojibakeMarkers(value: string) {
  const matches = String(value || "").match(new RegExp(MOJIBAKE_MARKER.source, "g"));
  return matches ? matches.length : 0;
}

function decodeUtf8BytesFromString(
  input: string,
  cp1252Reverse: Record<number, number>,
): string {
  const bytes: number[] = [];
  for (const ch of input) {
    const code = ch.charCodeAt(0);
    if (code <= 0xff) {
      bytes.push(code);
      continue;
    }
    const mapped = cp1252Reverse[code];
    if (mapped === undefined) {
      throw new Error("non-latin1-char");
    }
    bytes.push(mapped);
  }
  return new TextDecoder("utf-8", { fatal: false }).decode(Uint8Array.from(bytes));
}

function repairDisplayText(value?: string | null) {
  const raw = String(value || "");
  if (!raw) return raw;

  const looksMojibake = MOJIBAKE_MARKER.test(raw);
  if (!looksMojibake) return raw;

  const cp1252Reverse: Record<number, number> = {
    0x20ac: 0x80,
    0x201a: 0x82,
    0x0192: 0x83,
    0x201e: 0x84,
    0x2026: 0x85,
    0x2020: 0x86,
    0x2021: 0x87,
    0x02c6: 0x88,
    0x2030: 0x89,
    0x0160: 0x8a,
    0x2039: 0x8b,
    0x0152: 0x8c,
    0x017d: 0x8e,
    0x2018: 0x91,
    0x2019: 0x92,
    0x201c: 0x93,
    0x201d: 0x94,
    0x2022: 0x95,
    0x2013: 0x96,
    0x2014: 0x97,
    0x02dc: 0x98,
    0x2122: 0x99,
    0x0161: 0x9a,
    0x203a: 0x9b,
    0x0153: 0x9c,
    0x017e: 0x9e,
    0x0178: 0x9f,
  };

  const decodeCandidate = (input: string) => {
    try {
      const decoded = decodeUtf8BytesFromString(input, cp1252Reverse);
      if (!decoded) return input;
      const before = countMojibakeMarkers(input);
      const after = countMojibakeMarkers(decoded);
      return after < before ? decoded : input;
    } catch {
      return input;
    }
  };

  // Try whole-string decode first.
  let candidate = decodeCandidate(raw);

  // If still noisy (mixed clean + mojibake), decode token-by-token.
  if (countMojibakeMarkers(candidate) > 0) {
    candidate = candidate.replace(/[^\s]+/g, (token) => decodeCandidate(token));
  }

  // One more pass can fix double-encoded fragments.
  if (countMojibakeMarkers(candidate) > 0) {
    candidate = decodeCandidate(candidate);
  }

  return candidate.trim() || raw;
}

function isMojibakeText(value: string) {
  return MOJIBAKE_MARKER.test(String(value || ""));
}

function isRawOrDebugLine(line: string) {
  const normalized = sanitizeText(line);
  if (!normalized) return true;
  const label = sanitizeText(normalized.split(":")[0] || "");
  const upper = label.toUpperCase();
  const upperNoIndex = upper.replace(/\s+\d+$/, "").trim();
  if (RAW_DEBUG_KEYS.has(upper) || RAW_DEBUG_KEYS.has(upperNoIndex)) return true;
  if (/^(debug|raw|source[_\s-]?key|structured section details)$/i.test(label)) return true;
  if (/^[A-Z0-9_]{4,}$/.test(label)) return true;
  return false;
}

function parseSectionLines(section?: HindiSection) {
  if (!section) return [] as ParsedLine[];
  return (section.blocks || [])
    .flatMap((block) =>
      String(block || "")
        .split(/\n+/)
        .map((line) => sanitizeText(line)),
    )
    .filter((line) => line.length > 0 && !isRawOrDebugLine(line))
    .map((line) => {
      const idx = line.indexOf(":");
      if (idx === -1) {
        if (isMojibakeText(line)) return { label: "", value: "" };
        if (!/[A-Za-z\u0900-\u097F0-9]/.test(line)) return { label: "", value: "" };
        return { label: "", value: line };
      }
      const rawLabel = sanitizeText(line.slice(0, idx));
      const rawValue = sanitizeText(line.slice(idx + 1));
      const invalidLabel =
        !rawLabel ||
        isMojibakeText(rawLabel) ||
        (rawLabel.replace(/\s+/g, "").length > 26 && !/\s/.test(rawLabel));
      if (isMojibakeText(rawValue)) return { label: "", value: "" };
      return {
        label: invalidLabel ? "" : rawLabel,
        value: rawValue,
      };
    })
    .filter((line) => line.value.length > 0);
}

function parseRawSectionLines(section?: HindiSection) {
  if (!section) return [] as string[];
  return (section.blocks || [])
    .flatMap((block) =>
      String(block || "")
        .split(/\n+/)
        .map((line) => repairDisplayText(String(line || "")).replace(/\*\*/g, "").trim()),
    )
    .filter((line) => line.length > 0);
}

function compactText(input: string, maxLength = 360) {
  const text = sanitizeText(input);
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1).trimEnd()}...`;
}

function resolveDisplayName(report: ReportResponse) {
  const normalized = report.content?.normalizedInput;
  const fallback = report.content?.input_normalized;
  const fullName = sanitizeText(
    String(normalized?.fullName || fallback?.name || "").trim(),
  );
  if (!fullName) return { firstName: "User", honorific: "User Ji" };
  const firstName = fullName.split(/\s+/)[0] || "User";
  return { firstName, honorific: `${firstName} Ji` };
}

function uniqueValues(values: string[]) {
  const seen = new Set<string>();
  return values.filter((value) => {
    const key = sanitizeText(value).toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

const SECTION_KEY_HINTS: Partial<Record<Exclude<PrintableSectionKey, "cover">, string[]>> = {
  charging: [
    "basic_charging_direction",
    "charging_direction",
    "charging_protocol",
  ],
  remedies: [
    "basic_remedies_table",
    "remedies_table",
    "remedy_cards",
    "remedies",
  ],
  tracker21Days: [
    "basic_21_day_tracker",
    "21_day_tracker",
    "tracker",
  ],
  summary: [
    "basic_summary_table_v2",
    "summary_table_v2",
    "summary_table",
    "summary",
  ],
  keyInsight: [
    "basic_key_insight",
    "key_insight",
    "core_insight",
  ],
  nextSteps: [
    "basic_next_steps",
    "next_steps",
    "action_plan",
  ],
  upgrade: [
    "basic_upgrade_path",
    "upgrade_path",
    "closing_summary",
    "cta",
  ],
  recommendation: [
    "basic_keep_change_verdict",
    "keep_change_verdict",
    "mobile_recommendation",
  ],
  lifePathContext: [
    "life_path_context",
    "mobile_life_number_compatibility",
    "mobile_life_compatibility",
    "basic_life_path_context",
  ],
  keyLifeAreas: [
    "key_life_areas",
    "impact_on_key_life_areas",
    "basic_key_life_areas",
    "life_area_impact",
  ],
};

function pickEffects(parsed: ParsedLine[]) {
  const positives = uniqueValues(
    parsed
      .filter((line) => /positive|सकारात्मक|strength|ताकत|influence/i.test(`${line.label} ${line.value}`))
      .map((line) => line.value),
  );

  const challenges = uniqueValues(
    parsed
      .filter((line) => /challenge|चुनौती|risk|जोखिम|negative|impulsiveness|अधीरता/i.test(`${line.label} ${line.value}`))
      .map((line) => line.value),
  );

  if (!positives.length || !challenges.length) {
    const fallback = uniqueValues(parsed.map((line) => line.value).filter(Boolean));
    if (!positives.length) positives.push(...fallback.slice(0, 5));
    if (!challenges.length) challenges.push(...fallback.slice(5, 8));
  }

  return {
    positives: positives.slice(0, 5),
    challenges: challenges.slice(0, 3),
  };
}

const LOSHU_LAYOUT = [
  [4, 9, 2],
  [3, 5, 7],
  [8, 1, 6],
];

function getMobileNumberFromReport(report: ReportResponse) {
  const normalized = report.content?.normalizedInput;
  const fallback = report.content?.input_normalized;
  const value = String(normalized?.mobileNumber || fallback?.mobile || "").replace(/\D/g, "");
  if (!value) return "";
  // Normalize to Indian 10-digit mobile representation for deterministic Lo Shu.
  if (value.length >= 10) return value.slice(-10);
  return value;
}

function getDigitFrequency(mobileNumber: string) {
  const counts: Record<number, number> = {
    0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0,
  };
  for (const char of mobileNumber.split("")) {
    const digit = Number(char);
    if (Number.isInteger(digit) && digit >= 0 && digit <= 9) counts[digit] += 1;
  }
  return counts;
}

function deriveLoShuFromReport(report: ReportResponse) {
  const mobile = getMobileNumberFromReport(report);
  const counts: Record<number, number> = getDigitFrequency(mobile);

  const present = Array.from({ length: 9 }, (_, idx) => idx + 1).filter((digit) => counts[digit] > 0);
  const missing = Array.from({ length: 9 }, (_, idx) => idx + 1).filter((digit) => counts[digit] === 0);
  const repeating = Array.from({ length: 9 }, (_, idx) => idx + 1).filter((digit) => counts[digit] > 1);
  const repeatingText = repeating.map((digit) => `${digit} (${counts[digit]}x)`);

  return {
    mobile,
    counts,
    present,
    missing,
    repeatingText,
  };
}

function toNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value.trim());
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function extractNumberFromText(value: unknown): number | undefined {
  const text = sanitizeText(String(value || ""));
  if (!text) return undefined;
  const match = text.match(/\b(11|22|33|[1-9])\b/);
  if (!match) return undefined;
  return Number(match[1]);
}

function reduceToDigit(value: number, keepMasters = false): number {
  let current = Math.abs(Math.trunc(value));
  while (current > 9 && (!keepMasters || ![11, 22, 33].includes(current))) {
    current = String(current)
      .split("")
      .reduce((sum, ch) => sum + Number(ch), 0);
  }
  return current;
}

function deriveLifePathFromDob(rawDob: unknown): number | undefined {
  const text = String(rawDob || "");
  const digits = text.replace(/\D/g, "");
  if (!digits) return undefined;
  const total = digits.split("").reduce((sum, ch) => sum + Number(ch), 0);
  return reduceToDigit(total, true);
}

function deriveMobileVibration(rawMobile: unknown): number | undefined {
  const digits = String(rawMobile || "").replace(/\D/g, "");
  if (!digits) return undefined;
  const total = digits.split("").reduce((sum, ch) => sum + Number(ch), 0);
  return reduceToDigit(total, false);
}

function firstDefinedNumber(...values: unknown[]): number | undefined {
  for (const value of values) {
    const parsed = toNumber(value) ?? extractNumberFromText(value);
    if (parsed !== undefined) return parsed;
  }
  return undefined;
}

function LoShuVisual({
  mobile,
  counts,
}: {
  mobile: string;
  counts: Record<number, number>;
}) {
  return (
    <div className="report-loshu-panel avoid-break">
      <p className="report-loshu-title">आपका नंबर | Your Number: {mobile || "N/A"}</p>
      <div className="report-loshu-matrix">
        {LOSHU_LAYOUT.map((row, rowIdx) => (
          <div key={`row-${rowIdx}`} className="report-loshu-row">
            {row.map((digit) => (
              <div key={`digit-${digit}`} className="report-loshu-cell">
                <span className="report-loshu-digit">{digit}</span>
                <span className="report-loshu-status">{counts[digit] > 0 ? `✓ (${counts[digit]})` : "✗ (0)"}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="report-loshu-frequency">
        {Array.from({ length: 10 }, (_, digit) => digit).map((digit) => (
          <span key={`freq-${digit}`} className="report-loshu-frequency-chip">
            {digit}: {counts[digit]}
          </span>
        ))}
      </div>
      <p className="report-loshu-legend">✓ = मौजूद अंक | ✗ = अनुपस्थित अंक</p>
    </div>
  );
}

function resolveSectionByKey(
  key: Exclude<PrintableSectionKey, "cover">,
  sectionPool: HindiSection[],
) {
  const hintedKeys = SECTION_KEY_HINTS[key] || [];
  if (hintedKeys.length) {
    const exactIndex = sectionPool.findIndex((section) =>
      hintedKeys.some((hint) => section.key.toLowerCase().includes(hint.toLowerCase())),
    );
    if (exactIndex >= 0) {
      return sectionPool.splice(exactIndex, 1)[0];
    }
  }

  const matcherSet = PRINT_PAGE_META[key].matchers;
  const scored = sectionPool
    .map((section, idx) => {
      const haystack = `${section.key} ${section.title} ${(section.blocks || []).join(" ")}`.toLowerCase();
      const score = matcherSet.reduce((total, token) => (haystack.includes(token.toLowerCase()) ? total + 1 : total), 0);
      return { idx, score };
    })
    .sort((a, b) => b.score - a.score);

  if (!scored.length) return undefined;
  if ((scored[0]?.score || 0) <= 0) return sectionPool.shift();
  const chosen = sectionPool.splice(scored[0].idx, 1)[0];
  return chosen;
}

function buildTemplateData(
  key: Exclude<PrintableSectionKey, "cover">,
  section: HindiSection | undefined,
  sectionIndex: number,
  report: ReportResponse,
): ReportSectionTemplateData {
  const meta = PRINT_PAGE_META[key];
  const parsed = parseSectionLines(section);
  const summaryItems = parsed
    .filter((line) => line.label && line.value)
    .slice(0, 6)
    .map((line) => ({ label: line.label, value: compactText(line.value, 88) }));
  const freeLines = uniqueValues(parsed.filter((line) => !line.label).map((line) => line.value));
  const bullets = uniqueValues(
    parsed
      .filter((line) => !line.label)
      .map((line) => line.value)
      .filter(Boolean),
  )
    .slice(0, 5)
    .map((line) => compactText(line, 120));
  const takeaways = uniqueValues([
    ...summaryItems.slice(0, 2).map((item) => `${item.label}: ${item.value}`),
    ...bullets.slice(0, 2),
  ]).slice(0, 4);

  const bodyTextSource = compactText(
    freeLines.join(" ") || section?.subtitle || section?.title || "Section summary is being prepared.",
    560,
  );

    if (key === "loShuGrid") {
    const { honorific } = resolveDisplayName(report);
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const challenge = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );
    const loShu = deriveLoShuFromReport(report);

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "visual",
      tag: meta.tag,
      summaryItems: [
        { label: "आपका नंबर | Your Number", value: loShu.mobile || "N/A" },
        { label: "मौजूद अंक | Present", value: loShu.present.join(", ") || "--" },
        { label: "अनुपस्थित अंक | Missing", value: loShu.missing.join(", ") || "--" },
        { label: "दोहराए अंक | Repeating", value: loShu.repeatingText.join(", ") || "--" },
        { label: "चुनौती लिंक | Challenge Link", value: challenge || "consistency" },
      ],
      highlightValue: loShu.missing.length ? loShu.missing.join(", ") : "Balanced Grid",
      bodyTitle: `लो शू व्याख्या | Lo Shu Interpretation (${honorific})`,
      bodyText: `${honorific}, आपके लो शू ग्रिड में अनुपस्थित अंक आपकी चुनौती "${challenge}" से सीधे जुड़े हैं। नीचे matrix और frequency map के आधार पर मौजूद व कमजोर ऊर्जा का सार दिया गया है।`,
      notes: [],
      bullets: [
        `अनुपस्थित अंक (${loShu.missing.join(", ") || "none"}) उन क्षेत्रों को दिखाते हैं जहाँ structured effort की जरूरत है।`,
        `दोहराए अंक (${loShu.repeatingText.join(", ") || "none"}) संबंधित energies को amplify करते हैं, इसलिए संतुलन जरूरी है।`,
        `Grid से स्पष्ट है कि आपका communication और execution rhythm मोबाइल पैटर्न से प्रभावित हो रहा है।`,
      ],
      takeaways: [
        `Missing: ${loShu.missing.join(", ") || "None"}`,
        `Repeating: ${loShu.repeatingText.join(", ") || "None"}`,
        `Focus: ${challenge || "consistency"}`,
      ],
      visualType: "matrix",
      visualNode: <LoShuVisual mobile={loShu.mobile} counts={loShu.counts} />,
    };
  }

  if (key === "mobileEnergy") {
    const { honorific } = resolveDisplayName(report);
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const userFocus = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );

    const mobileSummary = summaryItems.filter((item) =>
      /mobile|मोबाइल|vibration|मूल अंक|planet|ग्रह|element|तत्व|energy|ऊर्जा/i.test(item.label),
    );
    const mobileNumber = mobileSummary.find((item) => /mobile|मोबाइल/i.test(item.label))?.value || "N/A";
    const vibration = mobileSummary.find((item) => /vibration|मूल अंक/i.test(item.label))?.value || "N/A";
    const planet = mobileSummary.find((item) => /planet|ग्रह/i.test(item.label))?.value || "N/A";
    const element = mobileSummary.find((item) => /element|तत्व/i.test(item.label))?.value || "N/A";
    const energy = mobileSummary.find((item) => /energy|ऊर्जा/i.test(item.label))?.value || "N/A";

    const personalBullets = uniqueValues([
      `${honorific}, आपका मोबाइल नंबर ${mobileNumber} आपकी दैनिक communication frequency को सीधे प्रभावित करता है।`,
      `आपका मूल अंक ${vibration} है, जो आपकी प्रतिक्रिया शैली और निर्णय गति पर असर डालता है।`,
      `इस नंबर का ग्रह ${planet} है, इसलिए आपकी ऊर्जा में उसी ग्रह का behavioral pattern अधिक दिखता है।`,
      `आपका तत्व ${element} होने से आप stress को उसी element की प्रकृति के अनुसार process करते हैं।`,
      `प्रमुख ऊर्जा "${energy}" यह बताती है कि आप किस mode में सबसे अच्छा perform करते हैं।`,
      `${honorific}, आपका primary focus "${userFocus}" है, इसलिए इस नंबर की ऊर्जा को उसी दिशा में channel करना सबसे जरूरी है।`,
      `दिन की शुरुआत में 1 स्पष्ट priority तय करके इस vibration की scattered energy को focused output में बदला जा सकता है।`,
      `आपके लिए key intent: "मैं अपनी मोबाइल ऊर्जा को अनुशासन, स्पष्टता और निरंतरता में बदल रहा हूँ।"`,
    ]).map((item) => compactText(item, 180));

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "insight",
      tag: meta.tag,
      summaryItems: mobileSummary.slice(0, 5),
      highlightValue: mobileSummary[0]?.value || "",
      bodyTitle: `व्यक्तिगत अंतर्दृष्टि | Personal Insights (${honorific})`,
      bodyText: `${honorific}, नीचे दिए गए बिंदु आपके mobile vibration का practical प्रभाव बताते हैं:`,
      notes: [],
      bullets: personalBullets,
      takeaways: uniqueValues(
        mobileSummary.slice(0, 2).map((item) => `${item.label}: ${item.value}`),
      ),
      visualType: "none",
    };
  }

  if (key === "mobileEffects") {
    const { honorific } = resolveDisplayName(report);
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const challenge = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );
    const effects = pickEffects(parsed);

    const bulletRows = [
      ...effects.positives.map((item) => `Positive: ${compactText(item, 140)}`),
      ...effects.challenges.map((item) => `Challenge: ${compactText(item, 140)}`),
    ];

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "analysis",
      tag: meta.tag,
      summaryItems: [
        { label: "सकारात्मक प्रभाव | Positive", value: `${effects.positives.length} बिंदु` },
        { label: "संभावित चुनौतियाँ | Challenges", value: `${effects.challenges.length} बिंदु` },
        { label: "प्राथमिक फोकस लिंक | Focus Link", value: challenge || "consistency" },
      ],
      highlightValue: `${effects.positives.length} Strengths | ${effects.challenges.length} Challenges`,
      bodyTitle: `व्यक्तिगत प्रभाव | Personal Effects (${honorific})`,
      bodyText: `${honorific}, आपके मोबाइल vibration के प्रभाव नीचे actionable format में दिए गए हैं, ताकि आप सीधे अपने "${challenge}" फोकस पर काम कर सकें।`,
      notes: [],
      bullets: bulletRows,
      takeaways: uniqueValues([
        ...effects.positives.slice(0, 2),
        ...effects.challenges.slice(0, 1),
      ]).map((item) => compactText(item, 110)),
      visualType: "none",
    };
  }

  if (key === "keyLifeAreas") {
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const challenge = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );

    const rowLike = parsed.filter((line) =>
      /life_area_row|consistency|confidence|financial|career|decision|self-expression|निरंतरता|आत्मविश्वास|वित्तीय|करियर|निर्णय|अभिव्यक्ति/i.test(
        `${line.label} ${line.value}`,
      ),
    );

    const areaRows = (rowLike.length ? rowLike : parsed)
      .filter((line) => String(line.value || "").trim())
      .slice(0, 6)
      .map((line, idx) => ({
        label: line.label || `LIFE_AREA_ROW ${idx + 1}`,
        value: String(line.value || "").trim(),
      }));

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "grid",
      tag: meta.tag,
      summaryItems: areaRows,
      highlightValue: `${areaRows.length} Life Areas`,
      bodyTitle: "प्रमुख जीवन प्रभाव | Key Life Area Impact",
      bodyText: `प्राथमिक चुनौती "${challenge}" के आधार पर नीचे प्रत्येक जीवन क्षेत्र का विस्तृत प्रभाव दिया गया है।`,
      notes: [],
      bullets: areaRows.map((row) => `${row.label}: ${row.value}`),
      takeaways: [`Focus: ${challenge}`],
      visualType: "none",
    };
  }

  if (key === "recommendation") {
    const { honorific } = resolveDisplayName(report);
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || deterministic.basic_mobile_core || {}) as Record<string, any>;
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const challenge = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );

    const verdictRaw = sanitizeText(
      String(
        basicMobileCore.verdict ||
        parsed.find((line) => /verdict|निर्णय|recommendation/i.test(`${line.label} ${line.value}`))?.value ||
        "MANAGE",
      ),
    ).toUpperCase();

    const verdictNormalized =
      /CHANGE|बदल/.test(verdictRaw) ? "CHANGE"
        : /KEEP|रख/.test(verdictRaw) ? "KEEP"
          : "MANAGE";

    const verdictDisplayMap: Record<string, string> = {
      KEEP: "रखें (KEEP)",
      MANAGE: "संभालें (MANAGE)",
      CHANGE: "बदलें (CHANGE)",
    };

    const compatibility = sanitizeText(
      String(
        (basicMobileCore.compatibility || {}).label ||
        (basicMobileCore.compatibility || {}).level ||
        (deterministic.mobile_life_compatibility || {}).label ||
        (deterministic.mobile_life_compatibility || {}).level ||
        "Moderate / मध्यम",
      ),
    );
    const missingDigits = Array.isArray((basicMobileCore.lo_shu || {}).missing)
      ? (basicMobileCore.lo_shu || {}).missing.map((d: number | string) => String(d))
      : [];
    const repeatingDigits = Array.isArray((basicMobileCore.lo_shu || {}).repeating)
      ? (basicMobileCore.lo_shu || {}).repeating.map((row: Record<string, any>) => `${row.digit} (${row.count}x)`)
      : [];
    const suggestions = (basicMobileCore.suggestions || {}) as Record<string, any>;
    const preferredVibrations = Array.isArray(suggestions.preferred_vibrations)
      ? suggestions.preferred_vibrations.map((v: number | string) => String(v)).join(", ")
      : "4, 6, 8";

    const reasoning = sanitizeText(
      String(
        basicMobileCore.verdict_reasoning ||
        parsed.find((line) => /reason|comment|क्यों|कारण/i.test(`${line.label} ${line.value}`))?.value ||
        `${honorific}, वर्तमान मोबाइल पैटर्न आपके "${challenge}" फोकस को प्रभावित कर रहा है; इसलिए निर्णय को remedies और consistency actions के साथ लागू करें।`,
      ),
    );

    const actionBullets =
      verdictNormalized === "CHANGE"
        ? [
          `नया नंबर लेते समय vibration ${preferredVibrations} को प्राथमिकता दें।`,
          `Missing digits (${missingDigits.join(", ") || "none"}) को cover करने वाले pattern चुनें।`,
          "पुराना नंबर 30 दिन dual-sim पर रखकर transition करें।",
        ]
        : verdictNormalized === "KEEP"
          ? [
            "मौजूदा नंबर रखें, लेकिन 21-दिवसीय tracker लगातार follow करें।",
            `Primary focus "${challenge}" के लिए daily fixed execution window रखें।`,
            "हर 7 दिन review करके communication और decision rhythm सुधारें।",
          ]
          : [
            "नंबर बदलने से पहले remedies + digital discipline 21 दिन लागू करें।",
            `Missing digits (${missingDigits.join(", ") || "none"}) पर corrective routine चलाएं।`,
            "अगर 30 दिन में drift कम न हो, तब suggested number structure अपनाएं।",
          ];

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "summary",
      tag: meta.tag,
      summaryItems: [
        { label: "निर्णय | Verdict", value: verdictDisplayMap[verdictNormalized] || verdictDisplayMap.MANAGE },
        { label: "अनुकूलता | Compatibility", value: compatibility || "Moderate / मध्यम" },
        { label: "Missing Digits", value: missingDigits.join(", ") || "--" },
        { label: "Repeating Digits", value: repeatingDigits.join(", ") || "--" },
      ],
      highlightValue: verdictDisplayMap[verdictNormalized] || verdictDisplayMap.MANAGE,
      bodyTitle: `निर्णय विश्लेषण | Verdict Analysis (${honorific})`,
      bodyText: reasoning,
      notes: [],
      bullets: actionBullets,
      takeaways: [
        `Verdict: ${verdictDisplayMap[verdictNormalized] || verdictDisplayMap.MANAGE}`,
        `Focus: ${challenge}`,
        `Preferred Vibrations: ${preferredVibrations}`,
      ],
      visualType: "none",
    };
  }

  if (key === "suggestedNumbers") {
    const { honorific } = resolveDisplayName(report);
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || deterministic.basic_mobile_core || {}) as Record<string, any>;
    const rawLines = parseRawSectionLines(section);

    const introCandidate =
      rawLines.find((line) => /^SUGGESTED_INTRO\s*:/i.test(line))?.replace(/^SUGGESTED_INTRO\s*:\s*/i, "").trim() ||
      sanitizeText(String(parsed.find((line) => /intro|सुझाए/iu.test(`${line.label} ${line.value}`))?.value || ""));
    const intro = introCandidate && !isMojibakeText(introCandidate)
      ? introCandidate
      : `${honorific}, नीचे दिए गए 3 नंबर पैटर्न आपकी वर्तमान mobile profile के आधार पर तैयार किए गए हैं।`;

    const optionRows = rawLines
      .filter((line) => /^SUGGESTED_OPTION\s*\d+\s*:/i.test(line))
      .map((line) => line.replace(/^SUGGESTED_OPTION\s*\d+\s*:\s*/i, "").trim())
      .map((line) => line.split("||").map((part) => sanitizeText(part)))
      .map((parts, idx) => ({
        title: parts[0] || `विकल्प ${idx + 1} | Option ${idx + 1}`,
        pattern: enforceIndiaMobilePatternStart(parts[1] || "--", idx),
        vibration: parts[2] || "--",
        keyDigits: parts[3] || "--",
        fills: parts[4] || "--",
        reason:
          sanitizeText(String(parts[5] || "")).length >= 16
            ? sanitizeText(String(parts[5] || ""))
            : "यह विकल्प missing digits और stability alignment सुधारने में मदद करता है।",
      }));

    const fallbackOptions = Array.isArray(basicMobileCore.suggested_numbers)
      ? (basicMobileCore.suggested_numbers as Array<Record<string, any>>).slice(0, 3).map((item, idx) => ({
        title: `विकल्प ${idx + 1} | Option ${idx + 1}`,
        pattern: enforceIndiaMobilePatternStart(String(item.pattern || "--"), idx),
        vibration: sanitizeText(String(item.vibration || "--")),
        keyDigits: Array.isArray(item.key_digits) ? item.key_digits.join(", ") : sanitizeText(String(item.key_digits || "--")),
        fills: "missing alignment",
        reason: sanitizeText(String(item.reason || "यह विकल्प profile alignment सुधारने के लिए सुझाया गया है।")),
      }))
      : [];

    const options = (optionRows.length ? optionRows : fallbackOptions).slice(0, 3);

    const steps = rawLines
      .filter((line) => /^SUGGESTED_STEP\s*\d+\s*:/i.test(line))
      .map((line) => line.replace(/^SUGGESTED_STEP\s*\d+\s*:\s*/i, "").trim())
      .map((line) => sanitizeText(line))
      .slice(0, 5);

    const fallbackSteps = [
      "अपने telecom provider (Jio/Airtel/Vi/BSNL) से उपलब्ध विकल्प पूछें।",
      "ऊपर दिए गए pattern के सबसे नज़दीक नंबर चुनें।",
      "अगर पहला विकल्प उपलब्ध न हो तो विकल्प 2/3 लें।",
      "नई SIM activate करके 30 दिन dual-SIM transition रखें।",
      "पुराना नंबर धीरे-धीरे phase-out करें और key contacts update करें।",
    ];

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "grid",
      tag: meta.tag,
      summaryItems: options.map((opt, idx) => ({
        label: `विकल्प ${idx + 1} | ${opt.title}`,
        value: `Pattern: ${opt.pattern} | Vibration: ${opt.vibration}`,
      })),
      highlightValue: `${options.length} Suggested Options`,
      bodyTitle: `नंबर चयन गाइड | Selection Guide (${honorific})`,
      bodyText: intro,
      notes: (steps.length ? steps : fallbackSteps).map((s, idx) => `${idx + 1}. ${s}`),
      bullets: options.map(
        (opt, idx) =>
          `विकल्प ${idx + 1}: ${opt.pattern} | Vibration ${opt.vibration} | Key Digits ${opt.keyDigits} | ${opt.reason}`,
      ),
      takeaways: [
        ...options.slice(0, 2).map((opt) => `V${opt.vibration}: ${opt.pattern}`),
        `Steps: ${(steps.length ? steps : fallbackSteps).length}`,
      ],
      visualType: "none",
      content: (
        <div className="report-custom-s7-content">
          <div className="report-custom-s7-grid">
            {options.length ? options.map((opt, idx) => (
              <article key={`s7-opt-${idx}`} className="report-custom-s7-card">
                <h5>{opt.title}</h5>
                <p><strong>Pattern:</strong> {opt.pattern}</p>
                <p><strong>Vibration:</strong> {opt.vibration}</p>
                <p><strong>Key Digits:</strong> {opt.keyDigits}</p>
                <p><strong>क्यों चुनें:</strong> {opt.reason}</p>
              </article>
            )) : (
              <article className="report-custom-s7-card">
                <h5>No options available</h5>
                <p>Suggested options are not present for this profile.</p>
              </article>
            )}
          </div>
          <section className="report-custom-panel report-custom-s7-steps">
            <h4>नया नंबर कैसे लें | How to Get These Numbers</h4>
            <ol>
              {(steps.length ? steps : fallbackSteps).map((step, idx) => (
                <li key={`s7-step-${idx}`}>{step}</li>
              ))}
            </ol>
          </section>
        </div>
      ),
    };
  }

  if (key === "remedies") {
    const { honorific } = resolveDisplayName(report);
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || deterministic.basic_mobile_core || {}) as Record<string, any>;
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const challenge = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );

    const rawLines = parseRawSectionLines(section);
    const pickByPrefix = (prefix: RegExp) =>
      rawLines.filter((line) => prefix.test(line)).map((line) => line.replace(prefix, "").trim());

    const intro =
      rawLines.find((line) => /^REMEDY_INTRO\s*:/i.test(line))?.replace(/^REMEDY_INTRO\s*:\s*/i, "").trim() ||
      `${honorific}, यदि आप तुरंत नंबर नहीं बदल सकते, तो नीचे दिए गए remedies को 21 दिन लगातार लागू करें।`;

    const comment =
      rawLines.find((line) => /^REMEDY_COMMENT\s*:/i.test(line))?.replace(/^REMEDY_COMMENT\s*:\s*/i, "").trim() ||
      `${honorific}, remedies का असर तभी दिखता है जब आप इन्हें daily routine और digital discipline के साथ जोड़ते हैं।`;

    const spiritualTitle =
      rawLines.find((line) => /^REMEDY_SP_TITLE\s*:/i.test(line))?.replace(/^REMEDY_SP_TITLE\s*:\s*/i, "").trim() ||
      "आध्यात्मिक और भौतिक उपाय | Spiritual & Physical Remedies";
    const digitalTitle =
      rawLines.find((line) => /^REMEDY_DG_TITLE\s*:/i.test(line))?.replace(/^REMEDY_DG_TITLE\s*:\s*/i, "").trim() ||
      "डिजिटल और दृश्य उपाय | Digital & Visual Remedies";
    const setupTitle =
      rawLines.find((line) => /^REMEDY_SETUP_TITLE\s*:/i.test(line))?.replace(/^REMEDY_SETUP_TITLE\s*:\s*/i, "").trim() ||
      "आपका व्यक्तिगत डिजिटल सेटअप | Your Personalized Digital Setup";
    const resetTitle =
      rawLines.find((line) => /^REMEDY_RESET_TITLE\s*:/i.test(line))?.replace(/^REMEDY_RESET_TITLE\s*:\s*/i, "").trim() ||
      "21-दिवसीय डिजिटल रीसेट योजना | 21-Day Digital Reset Plan";
    const checkTitle =
      rawLines.find((line) => /^REMEDY_CHECK_TITLE\s*:/i.test(line))?.replace(/^REMEDY_CHECK_TITLE\s*:\s*/i, "").trim() ||
      "दैनिक जाँच | Daily Check";

    const splitCols = (line: string) => line.split("||").map((part) => sanitizeText(part)).filter(Boolean);

    const spiritualRows = pickByPrefix(/^REMEDY_SP_ROW\s*\d+\s*:\s*/i)
      .map((line) => splitCols(line))
      .map((cols) => ({
        remedy: cols[0] || "--",
        action: sanitizeText(cols[1] || "--"),
        frequency: sanitizeText(cols[2] || "प्रतिदिन"),
      }))
      .slice(0, 5);

    const digitalRows = pickByPrefix(/^REMEDY_DG_ROW\s*\d+\s*:\s*/i)
      .map((line) => splitCols(line))
      .map((cols) => ({
        remedy: cols[0] || "--",
        action: sanitizeText(cols[1] || "--"),
        why: sanitizeText(cols[2] || "--"),
      }))
      .slice(0, 6);

    const setupRows = pickByPrefix(/^REMEDY_SETUP_ROW\s*\d+\s*:\s*/i)
      .map((line) => splitCols(line))
      .map((cols) => ({
        item: cols[0] || "--",
        recommendation: sanitizeText(cols[1] || "--"),
      }))
      .slice(0, 6);

    const resetRows = pickByPrefix(/^REMEDY_RESET_ROW\s*\d+\s*:\s*/i)
      .map((line) => splitCols(line))
      .map((cols) => ({
        week: cols[0] || "--",
        actions: sanitizeText(cols[1] || "--"),
      }))
      .slice(0, 3);

    const checklistRows = pickByPrefix(/^REMEDY_CHECK\s*\d+\s*:\s*/i)
      .map((line) => sanitizeText(line))
      .filter(Boolean)
      .slice(0, 5);

    const missingRudraksha = Array.isArray(basicMobileCore.missing_rudraksha)
      ? basicMobileCore.missing_rudraksha.map((item: unknown) => sanitizeText(String(item))).filter(Boolean)
      : [];
    const primaryRudraksha =
      missingRudraksha[0] ||
      `${sanitizeText(String((basicMobileCore.lo_shu || {}).missing?.[0] || 4))} मुखी रुद्राक्ष`;
    const mantra = sanitizeText(String(basicMobileCore.mantra || "ॐ मंगलाय नमः"));
    const gemstone = sanitizeText(String(basicMobileCore.gemstone || "मूंगा (Coral)"));
    const yantra = sanitizeText(String(basicMobileCore.yantra || "नवग्रह यंत्र"));
    const coverColor = sanitizeText(String(basicMobileCore.cover_color || "लाल या गहरा नीला"));
    const wallpaperTheme = sanitizeText(String(basicMobileCore.wallpaper_theme || "सूर्योदय या लाल-नारंगी थीम"));
    const dndMorning = sanitizeText(String(basicMobileCore.dnd_morning || "7:00-8:30 AM"));
    const dndEvening = sanitizeText(String(basicMobileCore.dnd_evening || "7:00-9:00 PM"));
    const nickname = sanitizeText(String(basicMobileCore.nickname_base || `${honorific.replace(/\s+Ji$/i, "")} Finance 4`));
    const contactPrefix = sanitizeText(String(basicMobileCore.contact_prefix_digit || 4));
    const folderLimit = sanitizeText(String(basicMobileCore.app_folder_limit || 4));
    const affirmation = sanitizeText(String(basicMobileCore.affirmation_base || "वित्तीय अनुशासन, स्थिरता, कर्ज मुक्ति"));

    const fallbackSpiritualRows = [
      { remedy: "मंत्र (Mantra)", action: `"${mantra}" का जाप करें`, frequency: "11 बार, सुबह-शाम" },
      { remedy: "रत्न (Gemstone)", action: `${gemstone} धारण करें`, frequency: "प्रतिदिन" },
      { remedy: "रुद्राक्ष (Rudraksha)", action: `${primaryRudraksha} धारण करें`, frequency: "प्रतिदिन" },
      { remedy: "यंत्र (Yantra)", action: `${yantra} कार्यक्षेत्र में रखें`, frequency: "स्थायी" },
    ];

    const fallbackDigitalRows = [
      { remedy: "मोबाइल कवर", action: `${coverColor} रंग का कवर रखें`, why: "ऊर्जा स्थिरता और फोकस बढ़ता है" },
      { remedy: "वॉलपेपर", action: `${wallpaperTheme}`, why: "दैनिक मानसिक intent सक्रिय होता है" },
      { remedy: "स्टेटस लाइन", action: `"${affirmation}"`, why: "संकल्प repeat होकर behavior shift होता है" },
      { remedy: "अपना नंबर", action: `अपना नंबर "${nickname}" नाम से सेव करें`, why: "हर बार देखने पर focus reminder मिलता है" },
      { remedy: "DND", action: `${dndMorning} और ${dndEvening} DND on रखें`, why: "निर्णय और execution के लिए deep-focus window बनती है" },
      { remedy: "फोल्डर ऑर्गनाइजेशन", action: `प्रति फोल्डर अधिकतम ${folderLimit} ऐप रखें`, why: "डिजिटल clutter कम होकर consistency बढ़ती है" },
    ];

    const fallbackSetupRows = [
      { item: "Mobile Cover", recommendation: coverColor },
      { item: "Wallpaper", recommendation: wallpaperTheme },
      { item: "Status Line", recommendation: affirmation },
      { item: "Your Saved Name", recommendation: nickname },
      { item: "Contact Prefix", recommendation: `${contactPrefix} -` },
      { item: "DND Schedule", recommendation: `${dndMorning} और ${dndEvening}` },
      { item: "App Folders", recommendation: `अधिकतम ${folderLimit} ऐप प्रति फोल्डर` },
    ];

    const fallbackResetRows = [
      { week: "सप्ताह 1 (दिन 1-7)", actions: "मंत्र + मोबाइल कवर + वॉलपेपर + अपना नंबर सही नाम से सेव करें" },
      { week: "सप्ताह 2 (दिन 8-14)", actions: `कॉन्टैक्ट में "${contactPrefix} -" जोड़ें + DND + स्टेटस लाइन अपडेट करें` },
      { week: "सप्ताह 3 (दिन 15-21)", actions: `फोल्डर ऑर्गनाइजेशन + ${yantra} + सभी सेटिंग्स स्थिर करें` },
    ];

    const fallbackChecklist = [
      "पहले 90 मिनट DND mode रखा?",
      "वॉलपेपर और कवर सही theme पर हैं?",
      "अपना नंबर सही nickname से सेव है?",
      "तय communication window follow हुई?",
      "आज मंत्र और primary remedy किया?",
    ];

    const finalSpiritualRows = spiritualRows.length ? spiritualRows : fallbackSpiritualRows;
    const finalDigitalRows = digitalRows.length ? digitalRows : fallbackDigitalRows;
    const finalSetupRows = setupRows.length ? setupRows : fallbackSetupRows;
    const finalResetRows = (resetRows.length ? resetRows : fallbackResetRows).slice(0, 3);
    const finalChecklist = (checklistRows.length ? checklistRows : fallbackChecklist).slice(0, 5);

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "analysis",
      tag: meta.tag,
      summaryItems: [
        { label: "Primary Mantra", value: mantra },
        { label: "Primary Rudraksha", value: primaryRudraksha },
        { label: "Yantra", value: yantra },
        { label: "DND Window", value: `${dndMorning} | ${dndEvening}` },
      ],
      highlightValue: "21-Day Remedy Flow",
      bodyTitle: `उपाय मार्गदर्शन | Remedy Guidance (${honorific})`,
      bodyText: sanitizeText(intro),
      notes: [],
      bullets: finalChecklist.map((line) => `[ ] ${line}`),
      takeaways: [
        `Mantra: ${compactText(mantra, 36)}`,
        `Rudraksha: ${compactText(primaryRudraksha, 28)}`,
        `Focus: ${compactText(challenge, 30)}`,
        `DND: ${compactText(`${dndMorning} | ${dndEvening}`, 34)}`,
      ],
      visualType: "none",
      content: (
        <div className="report-custom-s9">
          <div className="report-custom-s9-col">
            <section className="report-custom-panel">
              <h4>{spiritualTitle}</h4>
              <table className="report-custom-s9-table">
                <thead>
                  <tr>
                    <th>उपाय</th>
                    <th>क्या करें</th>
                    <th>आवृत्ति</th>
                  </tr>
                </thead>
                <tbody>
                  {finalSpiritualRows.map((row, idx) => (
                    <tr key={`s9-sp-${idx}`}>
                      <td>{row.remedy}</td>
                      <td>{row.action}</td>
                      <td>{row.frequency}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="report-custom-panel">
              <h4>{digitalTitle}</h4>
              <table className="report-custom-s9-table">
                <thead>
                  <tr>
                    <th>उपाय</th>
                    <th>क्या करें</th>
                    <th>क्यों</th>
                  </tr>
                </thead>
                <tbody>
                  {finalDigitalRows.map((row, idx) => (
                    <tr key={`s9-dg-${idx}`}>
                      <td>{row.remedy}</td>
                      <td>{row.action}</td>
                      <td>{row.why}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>

          <div className="report-custom-s9-col">
            <section className="report-custom-panel">
              <h4>{setupTitle}</h4>
              <table className="report-custom-s9-table report-custom-s9-table--compact">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {finalSetupRows.map((row, idx) => (
                    <tr key={`s9-setup-${idx}`}>
                      <td>{row.item}</td>
                      <td>{row.recommendation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="report-custom-panel">
              <h4>{resetTitle}</h4>
              <ul className="report-custom-s9-list">
                {finalResetRows.map((row, idx) => (
                  <li key={`s9-reset-${idx}`}>
                    <strong>{row.week}:</strong> {row.actions}
                  </li>
                ))}
              </ul>
            </section>

            <section className="report-custom-panel">
              <h4>{checkTitle}</h4>
              <ul className="report-custom-s9-list report-custom-s9-list--check">
                {finalChecklist.map((line, idx) => (
                  <li key={`s9-check-${idx}`}>[ ] {line}</li>
                ))}
              </ul>
              <p className="report-custom-s9-comment">{sanitizeText(comment)}</p>
            </section>
          </div>
        </div>
      ),
    };
  }

  if (key === "tracker21Days") {
    const { honorific } = resolveDisplayName(report);
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || deterministic.basic_mobile_core || {}) as Record<string, any>;
    const rawLines = parseRawSectionLines(section);

    const trackerRows = rawLines
      .filter((line) => /^TRACKER_ROW\s*\d+\s*:/i.test(line))
      .map((line) => line.replace(/^TRACKER_ROW\s*\d+\s*:\s*/i, "").trim())
      .map((line) => line.split("||").map((part) => sanitizeText(part)).filter(Boolean))
      .map((cols, idx) => ({
        week: cols[0] || `सप्ताह ${idx + 1}`,
        task: compactText(cols[1] || "--", 170),
        status: cols[2] || "[ ]",
      }))
      .slice(0, 3);

    const direction = sanitizeText(String((basicMobileCore.charging || {}).direction || "पूर्व"));
    const day = sanitizeText(String((basicMobileCore.charging || {}).day || "मंगलवार"));
    const mantra = sanitizeText(String(basicMobileCore.mantra || "ॐ मंगलाय नमः"));
    const dndMorning = sanitizeText(String(basicMobileCore.dnd_morning || "7:00-8:30 AM"));
    const dndEvening = sanitizeText(String(basicMobileCore.dnd_evening || "7:00-9:00 PM"));

    const fallbackRows = [
      {
        week: "सप्ताह 1 (दिन 1-7)",
        task: `मंत्र ("${mantra}" 11 बार सुबह-शाम) + चार्जिंग दिशा (${direction}, ${day}) + मोबाइल कवर अपडेट`,
        status: "[ ]",
      },
      {
        week: "सप्ताह 2 (दिन 8-14)",
        task: `DND सेट करें (${dndMorning}, ${dndEvening}) + स्टेटस लाइन और कॉन्टैक्ट संरचना लागू करें`,
        status: "[ ]",
      },
      {
        week: "सप्ताह 3 (दिन 15-21)",
        task: "सभी remedies सक्रिय रखें + दैनिक जाँच + प्रगति समीक्षा",
        status: "[ ]",
      },
    ];

    const finalRows = trackerRows.length ? trackerRows : fallbackRows;

    const checklist = [
      "[ ] आज मंत्र किया?",
      "[ ] आज चार्जिंग दिशा/समय follow किया?",
      "[ ] DND window maintain रही?",
      "[ ] आज का मुख्य financial/execution task पूरा हुआ?",
    ];

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "grid",
      tag: meta.tag,
      summaryItems: finalRows.map((row) => ({
        label: row.week,
        value: `${row.task} | स्थिति: ${row.status}`,
      })),
      highlightValue: "21-Day Execution Tracker",
      bodyTitle: `ट्रैकर निर्देश | Tracker Protocol (${honorific})`,
      bodyText: `${honorific}, नीचे 21-दिवसीय ट्रैकर दिया गया है। प्रत्येक सप्ताह के task को पूरा करके status चेक करें।`,
      notes: [],
      bullets: checklist,
      takeaways: [
        `Week Blocks: ${finalRows.length}`,
        `Daily Check: ${checklist.length} points`,
        `Focus: Consistency + Execution`,
      ],
      visualType: "none",
      content: (
        <div className="report-custom-s10">
          <section className="report-custom-panel report-custom-s10-table-wrap">
            <table className="report-custom-s10-table">
              <thead>
                <tr>
                  <th>सप्ताह | Week</th>
                  <th>कार्य | Tasks</th>
                  <th>स्थिति | Status</th>
                </tr>
              </thead>
              <tbody>
                {finalRows.map((row, idx) => (
                  <tr key={`s10-row-${idx}`}>
                    <td>{row.week}</td>
                    <td>{row.task}</td>
                    <td>{row.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="report-custom-panel">
            <h4>दैनिक जाँच | Daily Check (30 sec)</h4>
            <ul className="report-custom-s10-list">
              {checklist.map((item, idx) => (
                <li key={`s10-check-${idx}`}>{item}</li>
              ))}
            </ul>
          </section>
        </div>
      ),
    };
  }

  if (key === "summary") {
    const { honorific } = resolveDisplayName(report);
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || deterministic.basic_mobile_core || {}) as Record<string, any>;
    const rawLines = parseRawSectionLines(section);

    const summaryRows = rawLines
      .filter((line) => /^SUMMARY_ROW\s*\d+\s*:/i.test(line))
      .map((line) => line.replace(/^SUMMARY_ROW\s*\d+\s*:\s*/i, "").trim())
      .map((line) => line.split("||").map((part) => sanitizeText(part)).filter(Boolean))
      .map((cols) => ({
        field: cols[0] || "--",
        status: compactText(cols[1] || "--", 64),
        suggestion: compactText(cols[2] || "--", 78),
      }))
      .slice(0, 7);

    const missingDigits = Array.isArray((basicMobileCore.lo_shu || {}).missing)
      ? (basicMobileCore.lo_shu || {}).missing.map((d: unknown) => String(d)).join(", ")
      : "--";
    const repeatingDigits = Array.isArray((basicMobileCore.lo_shu || {}).repeating)
      ? (basicMobileCore.lo_shu || {}).repeating
          .map((row: Record<string, any>) => `${row.digit} (${row.count}x)`)
          .join(", ")
      : "--";
    const lifePath = sanitizeText(String(basicMobileCore.life_path || (deterministic.numbers || {}).life_path || "--"));
    const vibration = sanitizeText(String((basicMobileCore.mobile || {}).vibration || (deterministic.numbers || {}).mobile_vibration || "--"));
    const compatibility = sanitizeText(
      String(
        (basicMobileCore.compatibility || {}).label ||
        (basicMobileCore.compatibility || {}).level ||
        (deterministic.mobile_life_compatibility || {}).label ||
        "Moderate / मध्यम",
      ),
    );
    const verdict = sanitizeText(String(basicMobileCore.verdict || "संभालें (MANAGE)"));
    const mantra = sanitizeText(String(basicMobileCore.mantra || "ॐ मंगलाय नमः"));
    const rudraksha = sanitizeText(
      String(Array.isArray(basicMobileCore.missing_rudraksha) ? basicMobileCore.missing_rudraksha[0] : "4 मुखी रुद्राक्ष"),
    );
    const yantra = sanitizeText(String(basicMobileCore.yantra || "नवग्रह यंत्र"));

    const fallbackRows = [
      { field: "मोबाइल अंक | Mobile Vibration", status: vibration, suggestion: "4, 6, या 8 आधारित संतुलन अपनाएँ" },
      { field: "लो शू में अनुपस्थित अंक | Missing Digits", status: missingDigits || "--", suggestion: "नए पैटर्न में missing digits शामिल करें" },
      { field: "लो शू में दोहराए अंक | Repeating Digits", status: repeatingDigits || "--", suggestion: "ऊर्जा संतुलन हेतु repetition नियंत्रण रखें" },
      { field: "जीवन पथ | Life Path", status: lifePath || "--", suggestion: "निर्णय जीवन पथ alignment के अनुसार लें" },
      { field: "अनुकूलता | Compatibility", status: compatibility || "Moderate / मध्यम", suggestion: "21-दिवसीय tracker से alignment सुधारें" },
      { field: "सिफारिश | Recommendation", status: verdict || "संभालें (MANAGE)", suggestion: "निर्णय के अनुसार कार्य योजना लागू करें" },
      { field: "प्राथमिक उपाय | Primary Remedy", status: `${mantra} + ${rudraksha} + ${yantra}`, suggestion: "कम से कम 21 दिन नियमित लागू करें" },
    ];

    const finalRows = summaryRows.length ? summaryRows : fallbackRows;

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "summary",
      tag: meta.tag,
      summaryItems: finalRows.map((row) => ({
        label: row.field,
        value: `${row.status} | ${row.suggestion}`,
      })),
      highlightValue: `Summary for ${honorific}`,
      bodyTitle: `सारांश अवलोकन | Summary Snapshot (${honorific})`,
      bodyText: `${honorific}, नीचे आपकी वर्तमान स्थिति और सीधे लागू होने वाले सुझाव एक जगह दिए गए हैं।`,
      notes: [],
      bullets: finalRows.slice(0, 4).map((row) => `${row.field}: ${row.status}`),
      takeaways: [
        `Recommendation: ${compactText(verdict, 34)}`,
        `Compatibility: ${compactText(compatibility, 34)}`,
        `Primary Remedy: ${compactText(`${mantra} + ${rudraksha}`, 40)}`,
      ],
      visualType: "none",
      content: (
        <div className="report-custom-s11">
          <section className="report-custom-panel report-custom-s11-table-wrap">
            <table className="report-custom-s11-table">
              <thead>
                <tr>
                  <th>क्षेत्र | Field</th>
                  <th>आपकी स्थिति | Your Status</th>
                  <th>सुझाव | Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {finalRows.map((row, idx) => (
                  <tr key={`s11-row-${idx}`}>
                    <td>{row.field}</td>
                    <td>{row.status}</td>
                    <td>{row.suggestion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      ),
    };
  }

  if (key === "keyInsight") {
    const { honorific } = resolveDisplayName(report);
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || deterministic.basic_mobile_core || {}) as Record<string, any>;
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const challenge = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );
    const rawLines = parseRawSectionLines(section);

    const keyInsightRows = rawLines
      .filter((line) => /^KEY_INSIGHT(?:_P\d+)?\s*:/i.test(line))
      .map((line) => line.replace(/^KEY_INSIGHT(?:_P\d+)?\s*:\s*/i, "").trim())
      .map((line) => sanitizeText(line))
      .filter((line) => Boolean(line) && !isMojibakeText(line));

    const missingDigits = Array.isArray((basicMobileCore.lo_shu || {}).missing)
      ? (basicMobileCore.lo_shu || {}).missing.map((d: unknown) => String(d)).join(", ")
      : "--";
    const repeatingDigits = Array.isArray((basicMobileCore.lo_shu || {}).repeating)
      ? (basicMobileCore.lo_shu || {}).repeating
          .map((row: Record<string, any>) => `${row.digit} (${row.count}x)`)
          .join(", ")
      : "--";
    const verdict = sanitizeText(String(basicMobileCore.verdict || "संभालें (MANAGE)"));
    const vibration = sanitizeText(String((basicMobileCore.mobile || {}).vibration || "--"));
    const mantra = sanitizeText(String(basicMobileCore.mantra || "ॐ मंगलाय नमः"));
    const rudraksha = sanitizeText(
      String(Array.isArray(basicMobileCore.missing_rudraksha) ? basicMobileCore.missing_rudraksha[0] : "4 मुखी रुद्राक्ष"),
    );
    const yantra = sanitizeText(String(basicMobileCore.yantra || "नवग्रह यंत्र"));

    const defaultP1 = `${honorific}, आपके मोबाइल vibration ${vibration} और लो शू पैटर्न (missing: ${missingDigits}; repeating: ${repeatingDigits}) सीधे आपकी "${challenge}" चुनौती को प्रभावित कर रहे हैं। सही अनुशासन और focus channeling से यह pattern व्यावहारिक रूप से सुधर सकता है।`;
    const defaultP2 = `निर्णय: ${verdict}. यदि आप 21 दिन तक ${mantra}, ${rudraksha} और ${yantra} आधारित routine को लगातार लागू करते हैं, तो execution clarity और stability में स्पष्ट सुधार दिखाई देगा।`;

    const insightP1 = keyInsightRows[0] || defaultP1;
    const insightP2 = keyInsightRows[1] || defaultP2;

    const actionBullets = [
      `21 दिन तक बिना break remedy stack follow करें: ${mantra} + ${rudraksha} + ${yantra}.`,
      `Daily एक fixed execution slot रखें और उसे "${challenge}" challenge पर लागू करें।`,
      `हर 7 दिन review करें: क्या missing-digit behavior drift कम हो रहा है?`,
    ];

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "summary",
      tag: meta.tag,
      summaryItems: [
        { label: "निर्णय | Recommendation", value: verdict },
        { label: "मोबाइल अंक | Mobile Vibration", value: vibration || "--" },
        { label: "Missing Digits", value: missingDigits || "--" },
        { label: "Primary Remedy Stack", value: `${mantra} + ${rudraksha} + ${yantra}` },
      ],
      highlightValue: verdict,
      bodyTitle: `मुख्य अंतर्दृष्टि | Key Insight (${honorific})`,
      bodyText: insightP1,
      notes: [],
      bullets: [insightP2, ...actionBullets],
      takeaways: [
        `Verdict: ${compactText(verdict, 34)}`,
        `Challenge: ${compactText(challenge, 34)}`,
        `Remedy: ${compactText(`${mantra} + ${rudraksha}`, 44)}`,
      ],
      visualType: "none",
      content: (
        <div className="report-custom-s12">
          <section className="report-custom-panel report-custom-s12-quote">
            <blockquote>{insightP2}</blockquote>
          </section>
          <section className="report-custom-panel">
            <h4>कार्य प्राथमिकताएँ | Action Priorities</h4>
            <ul className="report-custom-s12-list">
              {actionBullets.map((item, idx) => (
                <li key={`s12-a-${idx}`}>{item}</li>
              ))}
            </ul>
          </section>
        </div>
      ),
    };
  }

  if (key === "nextSteps") {
    const { honorific } = resolveDisplayName(report);
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || deterministic.basic_mobile_core || {}) as Record<string, any>;
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const challenge = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );
    const verdict = sanitizeText(String(basicMobileCore.verdict || "संभालें (MANAGE)"));
    const rawLines = parseRawSectionLines(section);

    const nextRows = rawLines
      .filter((line) => /^NEXTSTEP_ROW\s*\d+\s*:/i.test(line))
      .map((line) => line.replace(/^NEXTSTEP_ROW\s*\d+\s*:\s*/i, "").trim())
      .map((line) => line.split("||").map((part) => sanitizeText(part)).filter(Boolean))
      .map((cols, idx) => ({
        want: cols[0] || `विकल्प ${idx + 1}`,
        upgradeTo: cols[1] || "--",
      }))
      .slice(0, 3);

    const actionRows = rawLines
      .filter((line) => /^NEXTSTEP_ACTION\s*\d+\s*:/i.test(line))
      .map((line) => line.replace(/^NEXTSTEP_ACTION\s*\d+\s*:\s*/i, "").trim())
      .map((line) => sanitizeText(line))
      .filter(Boolean)
      .slice(0, 3);

    const fallbackRows = [
      {
        want: "नाम अंक विज्ञान (Destiny, Soul Urge, Personality) की स्पष्टता",
        upgradeTo: "Standard Report",
      },
      {
        want: "संपूर्ण जीवन रणनीति, करियर-वित्त-संबंध-स्वास्थ्य की गहराई",
        upgradeTo: "Enterprise Report",
      },
    ];

    const fallbackActions = [
      "नया नंबर लें: सुझाए गए पैटर्न में से प्रोफाइल-अलाइन विकल्प चुनें।",
      `मौजूदा नंबर संभालें: ${verdict} के अनुसार 21-day tracker discipline से follow करें।`,
      "गहरी मार्गदर्शिका चाहें: Standard या Enterprise से advanced blueprint सक्रिय करें।",
    ];

    const finalRows = nextRows.length ? nextRows : fallbackRows;
    const finalActions = actionRows.length ? actionRows : fallbackActions;

    const closing =
      sanitizeText(
        rawLines.find((line) => /^NEXTSTEP_CLOSING\s*:/i.test(line))?.replace(/^NEXTSTEP_CLOSING\s*:\s*/i, "").trim() || "",
      ) ||
      `${honorific}, आपकी "${challenge}" यात्रा अब execution discipline के साथ अगले स्तर पर जाने के लिए तैयार है।`;

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "grid",
      tag: meta.tag,
      summaryItems: finalRows.map((row) => ({
        label: row.want,
        value: row.upgradeTo,
      })),
      highlightValue: "3 स्पष्ट अगले कदम | 3 Clear Next Moves",
      bodyTitle: `रणनीतिक अगले कदम | Strategic Next Steps (${honorific})`,
      bodyText: `${honorific}, नीचे आपकी वर्तमान स्थिति (${verdict}) और "${challenge}" फोकस के आधार पर अगले actionable कदम दिए गए हैं।`,
      notes: [],
      bullets: finalActions,
      takeaways: [
        `Current Verdict: ${compactText(verdict, 32)}`,
        `Primary Focus: ${compactText(challenge, 32)}`,
        "Next Move: चुनें और तुरंत 7-दिवसीय execution शुरू करें",
      ],
      visualType: "none",
      content: (
        <div className="report-custom-s13">
          <section className="report-custom-panel report-custom-s13-grid">
            {finalRows.map((row, idx) => (
              <article key={`s13-u-${idx}`} className="report-custom-s13-card">
                <h5>यदि चाहें | If You Want</h5>
                <p>{row.want}</p>
                <div className="report-custom-s13-badge">{row.upgradeTo}</div>
              </article>
            ))}
          </section>
          <section className="report-custom-panel">
            <h4>आपके 3 तत्काल विकल्प | Your 3 Immediate Choices</h4>
            <ul className="report-custom-s13-list">
              {finalActions.map((item, idx) => (
                <li key={`s13-a-${idx}`}>{item}</li>
              ))}
            </ul>
            <p className="report-custom-s13-note">{closing}</p>
          </section>
        </div>
      ),
    };
  }

  if (key === "upgrade") {
    const { firstName, honorific } = resolveDisplayName(report);
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || deterministic.basic_mobile_core || {}) as Record<string, any>;
    const rawLines = parseRawSectionLines(section);

    const upgradeRows = rawLines
      .filter((line) => /^UPGRADE_ROW\s*\d+\s*:/i.test(line))
      .map((line) => line.replace(/^UPGRADE_ROW\s*\d+\s*:\s*/i, "").trim())
      .map((line) => line.split("||").map((part) => sanitizeText(part)).filter(Boolean))
      .map((cols) => ({
        plan: cols[0] || "--",
        benefit: cols[1] || "--",
      }))
      .slice(0, 2);

    const fallbackRows = [
      {
        plan: "Standard Report",
        benefit: "Basic + Name Numerology: भाग्यांक, आत्मिक इच्छा, व्यक्तित्व और नाम सुधार दिशा",
      },
      {
        plan: "Enterprise Report",
        benefit: "Complete Life Blueprint: 34+ premium sections, 90-day strategy, career-finance-relationship-health depth",
      },
    ];

    const closingText =
      sanitizeText(
        rawLines.find((line) => /^CTA_TEXT\s*:/i.test(line))?.replace(/^CTA_TEXT\s*:\s*/i, "").trim() || "",
      ) ||
      `${honorific}, आपकी ऊर्जा और आपका अनुशासन मिलकर आपकी दिशा बदल सकते हैं — अब आपका अगला कदम ही आपका अगला परिणाम तय करेगा।`;

    const wowTagline =
      sanitizeText(
        rawLines.find((line) => /^CLOSING_TAGLINE\s*:/i.test(line))?.replace(/^CLOSING_TAGLINE\s*:\s*/i, "").trim() || "",
      ) ||
      "जब ऊर्जा को संकल्प मिलता है, तो भाग्य सिर्फ बदलता नहीं — वह चमक उठता है।";

    const mantra = sanitizeText(String(basicMobileCore.mantra || "ॐ मंगलाय नमः"));
    const verdict = sanitizeText(String(basicMobileCore.verdict || "संभालें (MANAGE)"));
    const finalRows = upgradeRows.length ? upgradeRows : fallbackRows;

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "summary",
      tag: meta.tag,
      summaryItems: finalRows.map((row) => ({
        label: row.plan,
        value: row.benefit,
      })),
      highlightValue: `धन्यवाद, ${firstName}`,
      bodyTitle: "समापन संदेश | Final Closing",
      bodyText: closingText,
      notes: [],
      bullets: [
        `आज से आपका focus: ${compactText(verdict, 32)} निर्णय को action में बदलना।`,
        `Daily anchor: "${mantra}" + 5 मिनट शांत planning + 1 priority execution.`,
        "हर सप्ताह review करें: क्या आपका व्यवहार अब आपकी इच्छित दिशा से align है?",
      ],
      takeaways: [
        `Thank You, ${firstName}`,
        compactText(wowTagline, 56),
        "Your journey begins now.",
      ],
      visualType: "none",
      content: (
        <div className="report-custom-s14">
          <section className="report-custom-panel report-custom-s14-upgrades">
            <h4>अपग्रेड पथ | Upgrade Path</h4>
            <div className="report-custom-s14-grid">
              {finalRows.map((row, idx) => (
                <article key={`s14-u-${idx}`} className="report-custom-s14-card">
                  <h5>{row.plan}</h5>
                  <p>{row.benefit}</p>
                </article>
              ))}
            </div>
          </section>
          <section className="report-custom-panel report-custom-s14-thank">
            <h4>Thank You, {firstName} Ji</h4>
            <p>{closingText}</p>
            <blockquote>{wowTagline}</blockquote>
          </section>
        </div>
      ),
    };
  }

  if (key === "charging") {
    const { honorific } = resolveDisplayName(report);
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || deterministic.basic_mobile_core || {}) as Record<string, any>;
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const challenge = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );

    const rawLines = parseRawSectionLines(section);
    const intro =
      rawLines.find((line) => /^CHARGING_INTRO\s*:/i.test(line))?.replace(/^CHARGING_INTRO\s*:\s*/i, "").trim() ||
      `${honorific}, यदि आप नंबर तुरंत नहीं बदलना चाहते, तो नीचे दी गई charging दिशा और विधि से ऊर्जा संतुलित करें।`;

    const chargingCore = (basicMobileCore.charging || {}) as Record<string, any>;
    const defaultDirection = sanitizeText(String(chargingCore.direction || "पूर्व (East) की ओर रखें"));
    const defaultDay = sanitizeText(String(chargingCore.day || "मंगलवार"));
    const defaultTime = sanitizeText(String(chargingCore.time || "सूर्योदय"));
    const defaultMethod = sanitizeText(String(chargingCore.method || "फोन को सही दिशा में रखकर 10-15 मिनट intent के साथ चार्ज करें।"));

    const chargingRows = rawLines
      .filter((line) => /^CHARGING_ROW\s*\d+\s*:/i.test(line))
      .map((line) => line.replace(/^CHARGING_ROW\s*\d+\s*:\s*/i, "").trim())
      .map((line) => {
        const split = line.includes(" | ") ? line.split(" | ") : line.split("|");
        const label = sanitizeText(split[0] || "");
        const value = sanitizeText(split.slice(1).join(" | ") || "");
        return { label, value };
      });

    const direction =
      chargingRows.find((row) => /direction|दिशा/i.test(row.label))?.value ||
      chargingRows[0]?.value ||
      defaultDirection;
    const bestTime =
      chargingRows.find((row) => /best time|समय/i.test(row.label))?.value ||
      chargingRows[1]?.value ||
      `${defaultDay} | ${defaultTime}`;
    const how =
      chargingRows.find((row) => /how|कैसे/i.test(row.label))?.value ||
      chargingRows[2]?.value ||
      defaultMethod;

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "insight",
      tag: meta.tag,
      summaryItems: [
        { label: "दिशा | Direction", value: direction || "--" },
        { label: "सर्वोत्तम समय | Best Time", value: bestTime || "--" },
        { label: "कैसे करें | How", value: how || "--" },
      ],
      highlightValue: direction || "--",
      bodyTitle: `चार्जिंग अनुष्ठान | Charging Ritual (${honorific})`,
      bodyText: sanitizeText(intro),
      notes: [],
      bullets: [
        `पहला कदम: फोन को ${direction} रखें और charging के समय intentional focus बनाए रखें।`,
        `दूसरा कदम: ${bestTime} के window में 10-15 मिनट ritual charging करें।`,
        `तीसरा कदम: "${challenge}" फोकस के लिए charging के दौरान स्पष्ट संकल्प लें।`,
        `${honorific}, इस protocol को कम से कम 21 दिन लगातार follow करें ताकि pattern stable हो।`,
      ],
      takeaways: [
        `Direction: ${compactText(direction, 42)}`,
        `Best Time: ${compactText(bestTime, 42)}`,
        `Focus: ${compactText(challenge, 32)}`,
      ],
      visualType: "none",
    };
  }

  if (key === "lifePathContext") {
    const { honorific } = resolveDisplayName(report);
    const contentAny = (report.content || {}) as Record<string, any>;
    const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
    const numbers = (deterministic.numbers || {}) as Record<string, any>;
    const basicMobileCore = (deterministic.basicMobileCore || {}) as Record<string, any>;
    const numerologyValues = (deterministic.numerologyValues || {}) as Record<string, any>;
    const pythagorean = (numerologyValues.pythagorean || {}) as Record<string, any>;
    const mobileAnalysis = (numerologyValues.mobile_analysis || {}) as Record<string, any>;
    const loshuGrid = (numerologyValues.loshu_grid || {}) as Record<string, any>;
    const mobileProfile = (deterministic.mobile_profile || {}) as Record<string, any>;
    const compatibility = (deterministic.mobile_life_compatibility || {}) as Record<string, any>;
    const loShu = (deterministic.lo_shu || {}) as Record<string, any>;
    const loShuDerived = deriveLoShuFromReport(report);
    const normalizedInput = report.content?.normalizedInput;
    const fallbackInput = report.content?.input_normalized;
    const normalizedAny = (normalizedInput || {}) as Record<string, any>;
    const fallbackAny = (fallbackInput || {}) as Record<string, any>;
    const challenge = sanitizeText(
      String(normalizedInput?.currentProblem || normalizedInput?.focusArea || fallbackInput?.current_problem || "consistency"),
    );

    const parsedAlignment = parsed.find((line) =>
      /alignment|compatibility/i.test(`${line.label} ${line.value}`),
    )?.value;
    const parsedLifePath = parsed.find((line) => /life path/i.test(line.label))?.value;
    const parsedMobileVibration = parsed.find((line) =>
      /mobile vibration|mobile total|mobile|vibration/i.test(line.label),
    )?.value;

    const lifePathNumber = firstDefinedNumber(
      numbers.bhagyank,
      numbers.life_path,
      numbers.lifePath,
      pythagorean.life_path_number,
      pythagorean.lifePathNumber,
      (contentAny.profileSnapshot || {}).lifePath,
      parsedLifePath,
      deriveLifePathFromDob(
        normalizedAny.dateOfBirth || normalizedAny.dob || fallbackAny.date_of_birth || fallbackAny.dateOfBirth,
      ),
    );
    const mobileVibrationNumber = firstDefinedNumber(
      numbers.mobile_total,
      numbers.mobile_vibration,
      numbers.mobileVibration,
      (basicMobileCore.mobile || {}).vibration,
      mobileAnalysis.mobile_vibration,
      mobileAnalysis.mobile_number_vibration,
      mobileAnalysis.mobile_total,
      parsedMobileVibration,
      deriveMobileVibration(getMobileNumberFromReport(report)),
    );

    const lifePath = lifePathNumber !== undefined ? String(lifePathNumber) : "--";
    const mobileVibration = mobileVibrationNumber !== undefined ? String(mobileVibrationNumber) : "--";
    const compatibilityLabel = sanitizeText(
      String(parsedAlignment || compatibility.label || compatibility.level || compatibility.alignment || "Moderate / मध्यम"),
    );

    const missingDigitsFromMobileCore = Array.isArray((basicMobileCore.lo_shu || {}).missing)
      ? (basicMobileCore.lo_shu || {}).missing
      : [];
    const missingDigitsFromNumerology = Array.isArray(loshuGrid.missing_numbers)
      ? loshuGrid.missing_numbers
      : [];
    const missingDigitsSource =
      loShuDerived.missing.length > 0
        ? loShuDerived.missing
        : missingDigitsFromMobileCore.length > 0
          ? missingDigitsFromMobileCore
          : missingDigitsFromNumerology.length > 0
            ? missingDigitsFromNumerology
            : Array.isArray(loShu.missing)
              ? loShu.missing
              : [];
    const missingDigits = missingDigitsSource.length > 0 ? missingDigitsSource.join(", ") : "--";

    const profileSummary = sanitizeText(String(mobileProfile.summary || ""));

    return {
      sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
      title: meta.title,
      subtitle: meta.subtitle,
      type: "insight",
      tag: meta.tag,
      summaryItems: [
        { label: "आपका जीवन पथ | Life Path", value: lifePath },
        { label: "मोबाइल कंपन | Mobile Vibration", value: mobileVibration },
        { label: "अनुकूलता | Alignment", value: compatibilityLabel || "Moderate / मध्यम" },
        { label: "ग्रिड गैप | Missing Digits", value: missingDigits || "--" },
      ],
      highlightValue: `Life Path ${lifePath}`,
      bodyTitle: `Life Path Insight | जीवन पथ अंतर्दृष्टि (${honorific})`,
      bodyText:
        profileSummary ||
        `${honorific}, आपका मोबाइल कंपन और जीवन पथ मिलकर आपके निर्णय व execution rhythm को प्रभावित करते हैं।`,
      notes: [],
      bullets: [
        `${honorific}, आपका Life Path ${lifePath} और Mobile Vibration ${mobileVibration} मिलकर daily behavior pattern बनाते हैं।`,
        `वर्तमान alignment: ${compatibilityLabel || "Moderate / मध्यम"} — यह आपके "${challenge}" फोकस पर सीधा प्रभाव डालता है।`,
        `Lo Shu missing digits (${missingDigits || "--"}) के कारण consistency और structure पर विशेष ध्यान जरूरी है।`,
        `अगले 21 दिनों में एक fixed execution routine रखने से यह alignment अधिक practical और stable बनेगा।`,
      ],
      takeaways: [
        `Life Path: ${lifePath}`,
        `Alignment: ${compatibilityLabel || "Moderate / मध्यम"}`,
        `Focus: ${challenge}`,
      ],
      visualType: "none",
    };
  }

  return {
    sectionNumber: String(sectionIndex + 1).padStart(2, "0"),
    title: meta.title,
    subtitle: meta.subtitle,
    type: meta.type,
    tag: meta.tag,
    summaryItems,
    highlightValue: summaryItems[0]?.value || compactText(section?.title || "", 48),
    bodyTitle: summaryItems[0]?.label || meta.tag,
    bodyText: bodyTextSource,
    notes: freeLines.slice(0, 3).map((line) => compactText(line, 120)),
    bullets,
    takeaways,
    visualType: meta.visualType,
  };
}

function PrintablePage({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`report-page${className ? ` ${className}` : ""}`}>
      <div className="page-content">{children}</div>
    </section>
  );
}

function renderMobileEnergyCustomPage(data: ReportSectionTemplateData) {
  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <div className="report-custom-s1">
            <div className="report-custom-s1__left">
              <KeyValueList items={data.summaryItems || []} />
              <HighlightValueBlock value={String(data.highlightValue || "")} />
            </div>
            <div className="report-custom-s1__right">
              <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
              <section className="report-custom-panel">
                <h4>व्यक्तिगत बिंदु | Personal Insights</h4>
                <ul>
                  {(data.bullets || []).slice(0, 8).map((item, idx) => (
                    <li key={`s1-b-${idx}`}>{item}</li>
                  ))}
                </ul>
              </section>
            </div>
          </div>
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderLoShuCustomPage(data: ReportSectionTemplateData) {
  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <div className="report-custom-s2">
            <section className="report-custom-panel report-custom-panel--matrix">
              {data.visualNode}
            </section>
            <div className="report-custom-s2__lower">
              <section className="report-custom-panel">
                <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={data.bullets || []} />
              </section>
              <section className="report-custom-panel">
                <KeyValueList items={data.summaryItems || []} />
              </section>
            </div>
          </div>
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderMobileEffectsCustomPage(data: ReportSectionTemplateData) {
  const rawBullets = (data.bullets || []).filter(Boolean);
  const positives = rawBullets
    .filter((item) => /^positive\s*:/i.test(String(item).trim()))
    .map((item) => String(item).replace(/^positive\s*:\s*/i, "").trim());
  const challenges = rawBullets
    .filter((item) => /^challenge\s*:/i.test(String(item).trim()))
    .map((item) => String(item).replace(/^challenge\s*:\s*/i, "").trim());

  const fallbackMid = Math.ceil(rawBullets.length / 2);
  const positiveRows = positives.length ? positives : rawBullets.slice(0, fallbackMid);
  const challengeRows = challenges.length ? challenges : rawBullets.slice(fallbackMid);

  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <div className="report-custom-s3">
            <section className="report-custom-panel">
              <h4>सकारात्मक प्रभाव | Positive Influence</h4>
              <ul>
                {positiveRows.slice(0, 5).map((item, idx) => (
                  <li key={`s3-p-${idx}`}>{item}</li>
                ))}
              </ul>
            </section>
            <section className="report-custom-panel">
              <h4>संभावित चुनौतियाँ | Potential Challenges</h4>
              <ul>
                {challengeRows.slice(0, 5).map((item, idx) => (
                  <li key={`s3-c-${idx}`}>{item}</li>
                ))}
              </ul>
            </section>
          </div>
          <section className="report-custom-panel">
            <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
            <KeyValueList items={(data.summaryItems || []).slice(0, 3)} />
          </section>
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderLifePathCustomPage(data: ReportSectionTemplateData) {
  const summary = data.summaryItems || [];
  const lifePath = summary.find((item) => /life path|जीवन पथ/i.test(item.label))?.value || "--";
  const vibration = summary.find((item) => /mobile vibration|मोबाइल कंपन/i.test(item.label))?.value || "--";
  const alignment = summary.find((item) => /alignment|अनुकूलता/i.test(item.label))?.value || "--";
  const missing = summary.find((item) => /missing|गैप/i.test(item.label))?.value || "--";

  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <section className="report-custom-panel report-custom-s4-hero">
            <div className="report-custom-s4-chip"><span>Life Path</span><strong>{lifePath}</strong></div>
            <div className="report-custom-s4-chip"><span>Mobile Vibration</span><strong>{vibration}</strong></div>
            <div className="report-custom-s4-chip"><span>Alignment</span><strong>{alignment}</strong></div>
            <div className="report-custom-s4-chip"><span>Missing Digits</span><strong>{missing}</strong></div>
          </section>

          <div className="report-custom-s4">
            <section className="report-custom-panel">
              <h4>जीवन पथ अंतर्दृष्टि | Life Path Insight</h4>
              <p className="report-custom-s4-text">{data.bodyText || "--"}</p>
            </section>
            <section className="report-custom-panel">
              <h4>व्याख्या बिंदु | Interpretive Points</h4>
              <ul>
                {(data.bullets || []).slice(0, 5).map((item, idx) => (
                  <li key={`s4-b-${idx}`}>{item}</li>
                ))}
              </ul>
            </section>
          </div>
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderKeyLifeAreasCustomPage(data: ReportSectionTemplateData) {
  const summaryItems = data.summaryItems || [];
  const lifeAreaLike = (text: string) =>
    /life_area_row|consistency|confidence|financial|career|decision|self-expression|निरंतरता|आत्मविश्वास|वित्तीय|करियर|निर्णय|अभिव्यक्ति/i.test(
      text,
    );
  const impactMarker = /(high|moderate|low|उच्च|मध्यम|निम्न)/i;

  const sourceRows = [
    ...summaryItems
      .filter((item) => lifeAreaLike(`${item.label} ${item.value}`))
      .map((item) => `${item.label}: ${item.value}`),
    ...(data.bullets || []),
    ...(data.takeaways || []).filter((line) => lifeAreaLike(line)),
  ].filter((line) => String(line || "").trim());

  const dedup = Array.from(new Set(sourceRows.map((line) => String(line).trim()))).slice(0, 8);

  const rows = dedup.map((line) => {
    const raw = String(line || "").replace(/^LIFE_AREA_ROW\s*\d+\s*:\s*/i, "").trim();
    const labelPart = raw.split(":")[0] || "";
    const valuePart = raw.includes(":") ? raw.split(":").slice(1).join(":").trim() : raw;
    const candidate = valuePart || labelPart || raw;

    const markerMatch = candidate.match(impactMarker);
    const markerIndex = markerMatch?.index ?? -1;
    const area =
      markerIndex > 0
        ? candidate.slice(0, markerIndex).trim()
        : (labelPart && !/^LIFE_AREA_ROW/i.test(labelPart) ? labelPart.trim() : candidate).trim();
    const meaning =
      markerIndex >= 0
        ? candidate.slice(markerIndex).trim()
        : candidate;

    let impact = "MODERATE";
    const lc = `${area} ${meaning}`.toLowerCase();
    if (/\bhigh\b|उच्च/.test(lc)) impact = "HIGH";
    else if (/\blow\b|निम्न/.test(lc)) impact = "LOW";
    else if (/\bmoderate\b|मध्यम/.test(lc)) impact = "MODERATE";

    const cleanedMeaning = meaning.trim();
    return {
      area: area || "Life Area",
      impact,
      meaning: cleanedMeaning || candidate,
    };
  }).slice(0, 6);

  const summaryMap = new Map((data.summaryItems || []).map((item) => [item.label, item.value]));
  const challenge =
    [...summaryMap.entries()].find(([k]) => /focus|challenge|फोकस|चुनौती/i.test(k))?.[1] ||
    data.takeaways?.find((t) => /focus/i.test(t)) ||
    "--";

  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <section className="report-custom-panel">
            <h4>प्राथमिक चुनौती | Primary Challenge</h4>
            <p className="report-custom-s5-challenge">{challenge}</p>
          </section>

          <section className="report-custom-panel report-custom-s5-table-wrap">
            <table className="report-custom-s5-table">
              <thead>
                <tr>
                  <th>जीवन क्षेत्र | Area</th>
                  <th>प्रभाव | Impact</th>
                  <th>आपके लिए अर्थ | What This Means</th>
                </tr>
              </thead>
              <tbody>
                {rows.length ? rows.map((row, idx) => (
                  <tr key={`s5-r-${idx}`}>
                    <td>{row.area}</td>
                    <td>{row.impact}</td>
                    <td>{row.meaning}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={3}>No area details available</td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderRecommendationCustomPage(data: ReportSectionTemplateData) {
  const summary = data.summaryItems || [];
  const verdict = summary.find((item) => /verdict|निर्णय/i.test(item.label))?.value || "संभालें (MANAGE)";
  const compatibility = summary.find((item) => /compatibility|अनुकूलता/i.test(item.label))?.value || "--";
  const missing = summary.find((item) => /missing/i.test(item.label))?.value || "--";
  const repeating = summary.find((item) => /repeating/i.test(item.label))?.value || "--";

  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <div className="report-custom-s6">
            <section className="report-custom-panel report-custom-s6-verdict">
              <h4>निर्णय | Verdict</h4>
              <strong>{verdict}</strong>
              <p>{data.bodyText || "--"}</p>
            </section>

            <section className="report-custom-panel">
              <h4>क्यों यह निर्णय? | Why This Decision</h4>
              <ul className="report-custom-s6-meta">
                <li><span>अनुकूलता | Compatibility:</span> <strong>{compatibility}</strong></li>
                <li><span>Missing Digits:</span> <strong>{missing}</strong></li>
                <li><span>Repeating Digits:</span> <strong>{repeating}</strong></li>
              </ul>
              <h4>अगले कदम | Action Steps</h4>
              <ul>
                {(data.bullets || []).slice(0, 4).map((item, idx) => (
                  <li key={`s6-b-${idx}`}>{item}</li>
                ))}
              </ul>
            </section>
          </div>
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderSuggestedNumbersCustomPage(data: ReportSectionTemplateData) {
  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <section className="report-custom-panel">
            <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
          </section>
          {data.content}
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderChargingCustomPage(data: ReportSectionTemplateData) {
  const summary = data.summaryItems || [];
  const direction = summary.find((item) => /direction|दिशा/i.test(item.label))?.value || "--";
  const bestTime = summary.find((item) => /time|समय/i.test(item.label))?.value || "--";
  const how = summary.find((item) => /how|कैसे/i.test(item.label))?.value || "--";

  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <div className="report-custom-s8">
            <section className="report-custom-panel report-custom-s8-left">
              <h4>चार्जिंग सार | Charging Snapshot</h4>
              <KeyValueList items={summary} />
              <HighlightValueBlock value={direction} />
            </section>
            <section className="report-custom-panel report-custom-s8-right">
              <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
              <h4>अनुष्ठान प्रोटोकॉल | Ritual Protocol</h4>
              <ul>
                {(data.bullets || []).slice(0, 4).map((item, idx) => (
                  <li key={`s8-b-${idx}`}>{item}</li>
                ))}
              </ul>
              <div className="report-custom-s8-method">
                <p><strong>Best Time:</strong> {bestTime}</p>
                <p><strong>How:</strong> {how}</p>
              </div>
            </section>
          </div>
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderRemediesCustomPage(data: ReportSectionTemplateData) {
  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <section className="report-custom-panel">
            <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
          </section>
          {data.content}
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 2)} />
    </ReportPageBackground>
  );
}

function renderTrackerCustomPage(data: ReportSectionTemplateData) {
  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <section className="report-custom-panel">
            <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
          </section>
          {data.content}
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderSummaryCustomPage(data: ReportSectionTemplateData) {
  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <section className="report-custom-panel">
            <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
          </section>
          {data.content}
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderKeyInsightCustomPage(data: ReportSectionTemplateData) {
  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <section className="report-custom-panel">
            <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
          </section>
          {data.content}
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderNextStepsCustomPage(data: ReportSectionTemplateData) {
  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <section className="report-custom-panel">
            <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
          </section>
          {data.content}
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderUpgradeCustomPage(data: ReportSectionTemplateData) {
  return (
    <ReportPageBackground theme={CUSTOM_TEMPLATE_THEME}>
      <SectionHeader
        sectionNumber={data.sectionNumber}
        title={data.title}
        subtitle={data.subtitle}
        tag={data.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>
          <section className="report-custom-panel">
            <HighlightValueBlock value={String(data.highlightValue || "")} />
            <InsightTextPanel title={data.bodyTitle} text={data.bodyText} bullets={[]} />
          </section>
          {data.content}
        </MainContentCard>
      </div>
      <FooterSummaryRibbon points={(data.takeaways || []).slice(0, 4)} />
    </ReportPageBackground>
  );
}

function renderSectionPageByKey(
  key: Exclude<PrintableSectionKey, "cover">,
  data: ReportSectionTemplateData,
) {
  if (key === "mobileEnergy") return renderMobileEnergyCustomPage(data);
  if (key === "loShuGrid") return renderLoShuCustomPage(data);
  if (key === "mobileEffects") return renderMobileEffectsCustomPage(data);
  if (key === "lifePathContext") return renderLifePathCustomPage(data);
  if (key === "keyLifeAreas") return renderKeyLifeAreasCustomPage(data);
  if (key === "recommendation") return renderRecommendationCustomPage(data);
  if (key === "suggestedNumbers") return renderSuggestedNumbersCustomPage(data);
  if (key === "charging") return renderChargingCustomPage(data);
  if (key === "remedies") return renderRemediesCustomPage(data);
  if (key === "tracker21Days") return renderTrackerCustomPage(data);
  if (key === "summary") return renderSummaryCustomPage(data);
  if (key === "keyInsight") return renderKeyInsightCustomPage(data);
  if (key === "nextSteps") return renderNextStepsCustomPage(data);
  if (key === "upgrade") return renderUpgradeCustomPage(data);
  return renderSectionPage(data);
}

export default function ReportPrintView({
  report,
  sections,
  coverPage,
}: {
  report: ReportResponse;
  sections: HindiSection[];
  coverPage: ReactNode;
}) {
  const reportVersionRaw = String(
    (report as any)?.content?.meta?.reportVersion || (report as any)?.content?.meta?.report_version || "",
  ).trim();
  const isNewContractReport = /^7(\.|$)/.test(reportVersionRaw);

  const filteredSections = sections.filter((section) => {
    const key = String(section?.key || "").trim().toLowerCase();
    if (!key) return false;
    if (key.startsWith("basic_")) return false;
    return true;
  });

  const PLAN_AWARE_SECTION_KEYS = new Set([
    "required_inputs",
    "core_purpose",
    "primary_focus",
    "deterministic_engine",
  ]);
  const isPlanAwareFlow = filteredSections.some((section) =>
    PLAN_AWARE_SECTION_KEYS.has(String(section?.key || "").trim().toLowerCase()),
  );

  if (isNewContractReport || isPlanAwareFlow) {
    if (!filteredSections.length) {
      const emptyData: ReportSectionTemplateData = {
        sectionNumber: "01",
        title: "Report Sections Unavailable",
        subtitle: "No compatible plan-aware sections were found for rendering.",
        type: "insight",
        tag: "Rendering Guard",
        bodyTitle: "Section Contract",
        bodyText: "Please regenerate this report so it uses the latest section contract.",
        bullets: [],
        takeaways: ["Legacy section payload was blocked for this report version."],
      };

      return (
        <div className="print-root" aria-hidden="false">
          <div className="report-print-view">
            {coverPage}
            <PrintablePage>{renderSectionPage(emptyData)}</PrintablePage>
          </div>
        </div>
      );
    }

    return (
      <div className="print-root" aria-hidden="false">
        <div className="report-print-view">
          {coverPage}
          {filteredSections.map((section, idx) => {
            const lines = (section.blocks || []).map((line) => String(line || "").trim()).filter(Boolean);
            const [firstLine, ...restLines] = lines;
            const summaryItems = lines
              .map((line) => {
                const parts = line.split(":");
                if (parts.length < 2) return null;
                const label = parts.shift()?.trim() || "";
                const value = parts.join(":").trim();
                if (!label || !value) return null;
                return { label, value };
              })
              .filter((item): item is { label: string; value: string } => Boolean(item))
              .slice(0, 6);

            const pageData: ReportSectionTemplateData = {
              sectionNumber: String(idx + 1).padStart(2, "0"),
              title: section.title || `Section ${idx + 1}`,
              subtitle: section.subtitle || "",
              type: summaryItems.length >= 3 ? "summary" : "insight",
              tag: "Section",
              summaryItems,
              highlightValue: summaryItems[0]?.value || firstLine || "--",
              bodyTitle: summaryItems[0]?.label || "Insight",
              bodyText: firstLine || "Details are being prepared.",
              bullets: restLines.slice(0, 8),
              takeaways: lines.slice(0, 4),
            };

            return (
              <PrintablePage key={`${section.key}-${idx}`}>
                {renderSectionPage(pageData)}
              </PrintablePage>
            );
          })}
        </div>
      </div>
    );
  }

  void report;
  const pool = [...filteredSections];

  return (
    <div className="print-root" aria-hidden="false">
      <div className="report-print-view">
        {coverPage}
        {PRINTABLE_SECTIONS.filter((key): key is Exclude<PrintableSectionKey, "cover"> => key !== "cover").map((key, idx) => {
          const matchedSection = resolveSectionByKey(key, pool);
          const data = buildTemplateData(key, matchedSection, idx, report);
          const pageClassName = key === "remedies" ? "report-page--remedies-split" : undefined;
          return (
            <PrintablePage key={key} className={pageClassName}>
              {renderSectionPageByKey(key, data)}
            </PrintablePage>
          );
        })}
      </div>
    </div>
  );
}

