import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";

import API from "../../services/api";
import {
  renderSectionPage,
  type ReportSectionTemplateData,
  type SectionTemplateType,
} from "./SectionPageTemplate";
import ReportPrintView from "./ReportPrintView";
import type {
  CanonicalReportSection,
  StructuredReportSection,
  CompatibilityBundle,
  CoreMetrics,
  DeterministicNumbers,
  HindiSection,
  InputNormalized,
  LoShuGrid,
  RemedyBundle,
  ReportResponse,
} from "../../types/report";

const ASSETS = {
  logo: "/report-assets/branding/numai_logo.webp",
  mandala: "/report-assets/sacred/mandala_bg.webp",
  om: "/report-assets/sacred/om_gold.webp",
  lotus: "/report-assets/lotus/lotus_gold.webp",
  chakra: "/report-assets/icons/chakra.webp",
  krishna: "/report-assets/cover/krishna.webp",
  ganesha: "/report-assets/cover/ganesha.webp",
  deities: {
    surya: "/report-assets/deities/surya.webp",
    chandra: "/report-assets/deities/chandra.webp",
    mangal: "/report-assets/deities/mangal.webp",
    budh: "/report-assets/deities/budh.webp",
    guru: "/report-assets/deities/guru.webp",
    shukra: "/report-assets/deities/shukra.webp",
    shani: "/report-assets/deities/shani.webp",
    rahu: "/report-assets/deities/rahu.webp",
    ketu: "/report-assets/deities/ketu.webp",
  },
} as const;

const LOSHU_LAYOUT = [
  [4, 9, 2],
  [3, 5, 7],
  [8, 1, 6],
];

function cx(...parts: Array<string | false | undefined | null>) {
  return parts.filter(Boolean).join(" ");
}

function formatDate(value?: string | null) {
  if (!value) return "Not Provided";
  const raw = String(value).trim();
  if (!raw) return "Not Provided";

  const dateOnly = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (dateOnly) {
    const year = Number(dateOnly[1]);
    const month = Number(dateOnly[2]) - 1;
    const day = Number(dateOnly[3]);
    const utcDate = new Date(Date.UTC(year, month, day));
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    }).format(utcDate);
  }

  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

function toNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function digitalRoot(value: number): number {
  let current = Math.abs(Math.trunc(value));
  while (current > 9) {
    current = String(current)
      .split("")
      .reduce((sum, digit) => sum + Number(digit), 0);
  }
  return current;
}

function deriveMulank(dateValue?: string | null): number | undefined {
  if (!dateValue) return undefined;
  const date = new Date(dateValue);
  if (!Number.isNaN(date.getTime())) {
    return digitalRoot(date.getUTCDate());
  }

  const match = String(dateValue).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return undefined;
  return digitalRoot(Number(match[3]));
}

function humanizeEnum(value?: string | null) {
  const raw = String(value || "").trim();
  if (!raw) return "Not Provided";

  const lowered = raw.toLowerCase();
  const lookup: Record<string, string> = {
    general_alignment: "General Alignment (सामान्य संतुलन)",
    career_growth: "Career Growth (करियर वृद्धि)",
    finance_debt: "Finance and Debt (वित्त और ऋण)",
    relationship: "Relationship (संबंध)",
    health_stability: "Health Stability (स्वास्थ्य स्थिरता)",
    male: "Male (पुरुष)",
    female: "Female (महिला)",
    other: "Other (अन्य)",
  };
  if (lookup[lowered]) return lookup[lowered];
  if (lookup[lowered.replace(/\s+/g, "_")]) return lookup[lowered.replace(/\s+/g, "_")];
  return raw.replace(/_/g, " ");
}

function getResolvedNumbers(report: ReportResponse): DeterministicNumbers {
  const contentAny = (report.content || {}) as Record<string, any>;
  const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
  const basicMobileCore = (deterministic.basicMobileCore || {}) as Record<string, any>;
  const canonical = report.content?.normalizedInput || {};
  const legacyInput = report.content?.input_normalized || {};
  const profile = contentAny.profileSnapshot as Record<string, any> | undefined;

  const direct = (deterministic.numbers || {}) as Record<string, any>;
  const numerologyValues = (deterministic.numerologyValues || {}) as Record<string, any>;
  const pythagorean = (numerologyValues.pythagorean || {}) as Record<string, any>;
  const chaldean = (numerologyValues.chaldean || {}) as Record<string, any>;
  const mobileAnalysis = (numerologyValues.mobile_analysis || {}) as Record<string, any>;
  const emailAnalysis = (numerologyValues.email_analysis || {}) as Record<string, any>;
  const personalYear = (deterministic.personal_year || {}) as Record<string, any>;

  return {
    mulank:
      toNumber(direct.mulank) ??
      deriveMulank(canonical.dateOfBirth || legacyInput.date_of_birth) ??
      toNumber(profile?.destiny),
    bhagyank: toNumber(direct.bhagyank) ?? toNumber(pythagorean.life_path_number) ?? toNumber(profile?.lifePath),
    name_energy: toNumber(direct.name_energy) ?? toNumber(chaldean.name_number) ?? toNumber(profile?.nameNumber),
    mobile_total:
      toNumber((basicMobileCore.mobile || {}).vibration) ??
      toNumber(mobileAnalysis.mobile_vibration) ??
      toNumber(mobileAnalysis.mobile_number_vibration) ??
      toNumber(direct.mobile_total) ??
      toNumber(mobileAnalysis.mobile_total) ??
      toNumber(contentAny?.deterministic?.numbers?.mobile_total),
    email_energy: toNumber(direct.email_energy) ?? toNumber(emailAnalysis.email_number),
    personal_year:
      toNumber(direct.personal_year) ??
      toNumber(personalYear.number) ??
      toNumber(personalYear.personal_year_number),
  };
}

function getSectionSortValue(section: HindiSection) {
  const title = String(section.title || "");
  const match = title.match(/^\s*(\d+)\./);
  const titleNumber = match ? Number(match[1]) : Number.MAX_SAFE_INTEGER;
  return [titleNumber, section.order ?? Number.MAX_SAFE_INTEGER] as const;
}

function adaptCanonicalSection(
  section: CanonicalReportSection | StructuredReportSection,
  index: number,
): HindiSection {
  if ("content" in section && !("summary" in section)) {
    const content = String(section.content || "").trim();
    const keyPoints = (section.keyPoints || []).filter((item) => String(item || "").trim());
    const logicalReason = String(section.logicalReason || "").trim();
    const rawKey = String(section.sectionKey || "").toLowerCase();
    const isLoShu = rawKey.includes("lo_shu") || rawKey.includes("loshu");
    const layout = isLoShu ? "diagnostic_grid" : String((section as any).layout || "premium_card");

    const blocks: string[] = [];
    if (content) blocks.push(content);
    if (keyPoints.length) blocks.push(...keyPoints);
    if (logicalReason) blocks.push(logicalReason);

    return {
      order: index + 1,
      key: section.sectionKey,
      title: section.sectionTitle || section.sectionTitleHindi || section.sectionTitleEnglish || "Report Section",
      subtitle: "",
      layout,
      blocks: blocks.filter((line) => String(line || "").trim()),
    };
  }

  const scoreLines = (section.scoreHighlights || [])
    .filter((item) => String(item?.label || "").trim() && String(item?.value || "").trim())
    .map((item) => `${item.label}: ${item.value}`);

  const blocks: string[] = [];
  const pushIf = (value?: string | null) => {
    const text = String(value || "").trim();
    if (text) blocks.push(text);
  };

  pushIf(section.summary);
  pushIf(section.keyStrength);
  pushIf(section.keyRisk);
  pushIf(section.practicalGuidance);

  if ((section.loadedEnergies || []).length) {
    blocks.push(`Key Traits: ${(section.loadedEnergies || []).join(", ")}`);
  }

  if (scoreLines.length) {
    blocks.push(...scoreLines);
  }

  const canonicalKey = String(section.sectionKey || "").toLowerCase();
  const canonicalIsLoShu = canonicalKey.includes("lo_shu") || canonicalKey.includes("loshu");
  const canonicalLayout = canonicalIsLoShu ? "diagnostic_grid" : String((section as any).layout || "premium_card");

  return {
    order: index + 1,
    key: section.sectionKey,
    title: section.sectionTitle,
    subtitle: "",
    layout: canonicalLayout,
    blocks: blocks.filter((line) => String(line || "").trim()),
  };
}

function polishHindiArtifacts(input: string) {
  return String(input || "")
    .replace(/\s+/g, " ")
    .trim();
}

const DETAIL_MOJIBAKE_MARKER = /(\u00C3|\u00C2|\u00E2|\u00F0|\u00E0|\uFFFD)/;

function countDetailMojibake(value: string) {
  const matches = String(value || "").match(new RegExp(DETAIL_MOJIBAKE_MARKER.source, "g"));
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
  const cleanPlaceholderArtifacts = (input: string) =>
    String(input || "")
      .replace(/\uFFFD+/g, " ")
      .replace(/\?{2,}/g, "")
      .replace(/\(\s*\)/g, "")
      .replace(/[|]{2,}/g, "|")
      .replace(/\s{2,}/g, " ")
      .trim();

  if (!DETAIL_MOJIBAKE_MARKER.test(raw)) {
    return polishHindiArtifacts(cleanPlaceholderArtifacts(raw) || raw);
  }

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
      const before = countDetailMojibake(input);
      const after = countDetailMojibake(decoded);
      return after < before ? decoded : input;
    } catch {
      return input;
    }
  };

  let candidate = decodeCandidate(raw);
  if (countDetailMojibake(candidate) > 0) {
    candidate = candidate.replace(/[^\s]+/g, (token) => decodeCandidate(token));
  }
  if (countDetailMojibake(candidate) > 0) {
    candidate = decodeCandidate(candidate);
  }

  return polishHindiArtifacts(cleanPlaceholderArtifacts(candidate.trim() || raw) || raw);
}

function cleanTitle(title: string, index: number) {
  const stripped = repairDisplayText(String(title || "")).replace(/^\s*\d+\.\s*/, "").trim();
  const lines = stripped
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) {
    return `${String(index).padStart(2, "0")}. Strategic Section\nरणनीतिक अनुभाग`;
  }
  lines[0] = `${String(index).padStart(2, "0")}. ${lines[0]}`;
  return lines.join("\n");
}

const PREMIUM_SECTION_TITLE_MAP: Record<string, string> = {
  profile: "Profile Intelligence\n(????????? ??????????)",
  dashboard: "Life Intelligence\n(???? ??????????)",
  executive_summary: "Strategic Overview\n(??????? ???)",
  core_numbers: "Core Numerology\n(??? ??? ???????)",
  number_interaction: "Number Dynamics\n(??? ????????)",
  personality_profile: "Personality Intelligence\n(?????????? ?????????)",
  focus_snapshot: "Current Focus Insights\n(??????? ????)",
  personal_year: "Yearly Guidance\n(??????? ??????????)",
  lucky_dates: "Favorable Timing\n(?????? ???)",
  color_alignment: "Energy Alignment\n(????? ??????)",
  remedy: "Action Remedies\n(????)",
  closing_summary: "Final Insights\n(????? ???)",
};

const SECTION_KEY_ALIAS_MAP: Record<string, string> = {
  profile_snapshot: "profile",
  executive_numerology_summary: "executive_summary",
  core_numbers_analysis: "core_numbers",
  number_interaction_analysis: "number_interaction",
  personality_intelligence: "personality_profile",
  current_problem_analysis: "focus_snapshot",
  personal_year_forecast: "personal_year",
  personal_year_direction: "personal_year",
  personal_year_insights: "personal_year",
  yearly_guidance: "personal_year",
  lucky_numbers_favorable_dates: "lucky_dates",
  remedies_lifestyle_adjustments: "remedy",
  closing_numerology_guidance: "closing_summary",
};

function resolvePremiumSectionTitle(sectionKey: string, fallbackTitle: string) {
  const normalizedKey = SECTION_KEY_ALIAS_MAP[sectionKey] || sectionKey;
  return PREMIUM_SECTION_TITLE_MAP[normalizedKey] || fallbackTitle;
}

function resolveReportName(report: ReportResponse) {
  const canonicalInput = report.content?.normalizedInput || {};
  const legacyInput = report.content?.input_normalized || {};
  return String(canonicalInput.fullName || legacyInput.name || "").trim();
}

function resolveFirstName(report: ReportResponse) {
  const fullName = resolveReportName(report);
  if (!fullName) return "??";
  const first = fullName.split(/\s+/).find(Boolean) || "??";
  return first;
}

const LIFE_PATH_MEANINGS: Record<number, string> = {
  1: "????? ????????? ??? ?? ???????, ??? ?? ???????? ?????? ?????? ????? ???",
  2: "????? ?????, ??????????? ?? ??????? ?? ??????? ???? ?? ????? ?????? ???",
  3: "????? ??????????, ?????????? ?? ?????????? ????? ?? ???????? ??????? ???",
  4: "????? ???????, ??????? ?? ????? ???? ????? ??? ????? ?? ?????? ????????? ???",
  5: "????? ????? ??????, ?? ???? ??????? ?? ???? ?? ????? ?? ????? ???",
  6: "????? ??????????, ?????? ?? ??????? ?? ?????? ?? ???? ????????? ????? ???? ???",
  7: "????? ?????????, ???????? ?? ????? ?? ???? ????? ?? ????? ????????? ???",
  8: "????? ??????-???????? ???, ??????? ?????? ?? ?????? ?? ???? ???? ?? ????? ???",
  9: "????? ??????, ?????? ????????? ?? ?????? ?????? ?? ?????? ????? ???",
};

const BHAGYA_MEANINGS: Record<number, string> = {
  1: "???? ??? ???? ????? ????? ?? ??????? ?? ?????? ???? ?????? ?? ????? ????? ???? ???",
  2: "???? ??? ????????, ????? ?? ???????? ?? ???? ???? ?? ????? ????",
  3: "???? ??? ?????, ????????? ?? ???????? ??????? ??? ????? ?? ??????? ???? ???? ???",
  4: "???? ??? ????????, ?????? ?? ????? ?? ??? ??? ?? ?????? ???? ????? ?????? ???? ????",
  5: "???? ??? ?? ????, ?????????? ?? ??????? ?????? ?? ????? ???? ????",
  6: "???? ??? ??????????, ???? ?? ??????? ?? ?????? ????? ?? ????? ???? ???",
  7: "???? ??? ?????, ??? ?? ????? ?? ??? ???? ?? ???? ?????? ?? ????? ???? ???",
  8: "???? ??? ??????? ???, ??????? ??????? ?? ??????? ?????? ?????? ?? ??? ???? ???",
  9: "???? ??? ?????? ????????? ?? ?????????? ?????? ????? ?? ?????? ???? ????",
};

const NAME_MEANINGS: Record<number, string> = {
  1: "???? ????? ?????, ???????????? ?? ?????????? ??? ????? ???",
  2: "???? ??? ????? ?? ???????? ?????? ?? ??? ????? ????? ??? ????? ???",
  3: "???? ????? ??? ??????????, ?????? ?? ?????? ????? ?? ?????? ????? ???",
  4: "???? ????????? ??? ????????, ????????? ?? ????? ?????????? ?????? ???",
  5: "???? ????? ??????, ?????? ?? ?????? ?? ??????? ???? ???? ???? ???",
  6: "???? ??? ?????, ????????? ?? ??????? ??? ??????? ???? ???? ???? ???",
  7: "???? ????? ?????, ??????? ?? ?????????? ?? ????????? ??? ?? ??????? ???",
  8: "???? ????????? ??? ??????, ?????? ?? ??????? ?? ????? ???????? ?????? ???",
  9: "???? ????? ??????, ???? ?? ?????? ????????? ?????? ?????? ???? ???? ???",
};

function resolveMetricMeaning(label: string, value: string | number, report: ReportResponse) {
  const rawLabel = repairDisplayText(label).toLowerCase();
  const numericValue = toNumber(value);
  if (numericValue === undefined) return String(value ?? "");

  const firstName = resolveFirstName(report);
  if (rawLabel.includes("???? ??") || rawLabel.includes("life path")) {
    const insight = LIFE_PATH_MEANINGS[numericValue] || "????? ????????? ??? ?? ????, ??????? ?? ??? ????? ?? ?????? ???";
    return `${numericValue} � ${firstName} ??, ???? ???? ?? ?? ${insight}`;
  }
  if (rawLabel.includes("?????") || rawLabel.includes("destiny")) {
    const insight = BHAGYA_MEANINGS[numericValue] || "???? ??? ?? ?????????? ?? ?? ?? ??? ???? ??? ???????? ???? ?????";
    return `${numericValue} � ${firstName} ??, ???? ???? ?? ?? ${insight}`;
  }
  if (rawLabel.includes("???") || rawLabel.includes("name number")) {
    const insight = NAME_MEANINGS[numericValue] || "???? ??? ?? ?????????? ?? ?? ???? ????? ?? ????? ???? ??-???? ????";
    return `${numericValue} � ${firstName} ??, ???? ???? ?? ?? ${insight}`;
  }
  return String(value ?? "");
}

function normalizeDisplayLabel(label: string) {
  const raw = repairDisplayText(String(label || "")).trim();
  if (!raw) return raw;
  const lowered = raw.toLowerCase();
  if (lowered.startsWith("summary") || lowered.startsWith("your core insight")) {
    return "Your Core Insight";
  }
  if (
    lowered.startsWith("key trait") ||
    lowered.startsWith("key strength") ||
    lowered.startsWith("your natural strength")
  ) {
    return "Your Natural Strength";
  }
  if (
    lowered.startsWith("potential challenge") ||
    lowered.startsWith("key risk") ||
    lowered.startsWith("your growth edge")
  ) {
    return "Your Growth Edge";
  }
  if (
    lowered.startsWith("practical suggestion") ||
    lowered.startsWith("practical guidance") ||
    lowered.startsWith("your action path")
  ) {
    return "Your Action Path";
  }
  if (lowered.startsWith("energy indicators") || lowered.startsWith("your key traits")) {
    return "Your Key Traits";
  }
  if (lowered.startsWith("key metric")) return "Key Metric";
  if (lowered.startsWith("key number")) return "Key Number";
  if (lowered.includes("life path number")) return "Life Path Number";
  if (lowered.includes("destiny number")) return "Destiny Number";
  if (lowered.includes("name number")) return "Name Number";
  if (lowered.startsWith("auspicious signal")) return "Insight Signal";
  if (lowered.startsWith("section insight")) return "Insight Signal";
  if (lowered.startsWith("core aura")) return "Insight Signal";
  return raw;
}

const INLINE_LABEL_NOISE = [
  "key signal",
  "key signals",
  "supporting signal",
  "supporting signals",
  "action point",
  "action points",
  "insight",
  "signature",
  "मुख्य संकेत",
  "सहायक संकेत",
  "कार्यवाही बिंदु",
  "मुख्य निष्कर्ष",
  "सिग्नेचर",
];

function parseLine(text: string) {
  const raw = repairDisplayText(String(text || "").replace(/\*\*/g, "")).trim();
  const colonIndex = raw.indexOf(":");
  if (colonIndex === -1) {
    const normalizedNoPipe = raw.replace(/\|/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
    const isNoiseOnly = INLINE_LABEL_NOISE.some((token) => normalizedNoPipe === token || normalizedNoPipe === token.toLowerCase());
    const isBilingualNoise =
      (normalizedNoPipe.includes("key signal") && normalizedNoPipe.includes("मुख्य संकेत")) ||
      (normalizedNoPipe.includes("supporting signal") && normalizedNoPipe.includes("सहायक संकेत")) ||
      (normalizedNoPipe.includes("action points") && normalizedNoPipe.includes("कार्यवाही बिंदु")) ||
      (normalizedNoPipe.includes("key takeaway") && normalizedNoPipe.includes("मुख्य निष्कर्ष"));
    if (isNoiseOnly || isBilingualNoise) {
      return { label: "", value: "" };
    }
    return { label: "", value: normalizeDisplayLabel(raw) };
  }

  const label = normalizeDisplayLabel(raw.slice(0, colonIndex).trim());
  const value = repairDisplayText(raw.slice(colonIndex + 1).trim());
  const normalizedLabel = label.toLowerCase();
  const isInlineNoise = INLINE_LABEL_NOISE.some((token) =>
    normalizedLabel.includes(token.toLowerCase()) || label.includes(token),
  );
  if (isInlineNoise) {
    return { label: "", value: value || normalizeDisplayLabel(raw) };
  }
  const isGenericMetric =
    /^Key Metric/i.test(label) ||
    /^Key Number/i.test(label) ||
    label.includes("?????? ??????") ||
    label.includes("?????? ??????");
  if (isGenericMetric) {
    const metricParts = value.match(/^(.+?)\s*[-��:]\s*(.+)$/);
    if (metricParts) {
      return {
        label: normalizeDisplayLabel(metricParts[1].trim()),
        value: metricParts[2].trim(),
      };
    }
  }

  return {
    label,
    value,
  };
}

function swatchColor(name: string) {
  const value = repairDisplayText(String(name || "")).toLowerCase();
  if (value.includes("????") || value.includes("white")) return "#ffffff";
  if (value.includes("????? ????") || value.includes("blue")) return "#c9ddff";
  if (value.includes("??????") || value.includes("silver")) return "#d7d7d7";
  if (value.includes("???") || value.includes("green")) return "#cfe7cf";
  if (value.includes("????") || value.includes("black")) return "#222222";
  if (value.includes("red") || value.includes("???")) return "#d77b7b";
  return "#ece3d1";
}

type EnergyColorToken = {
  key: string;
  en: string;
  hi: string;
  hex: string;
};

const ENERGY_COLOR_LIBRARY: EnergyColorToken[] = [
  { key: "blue", en: "Blue", hi: "\u0928\u0940\u0932\u093e", hex: "#1b57bc" },
  { key: "green", en: "Green", hi: "\u0939\u0930\u093e", hex: "#0f6a46" },
  { key: "red", en: "Red", hi: "\u0932\u093e\u0932", hex: "#b14945" },
  { key: "orange", en: "Orange", hi: "\u0928\u093e\u0930\u0902\u0917\u0940", hex: "#c8782d" },
  { key: "yellow", en: "Yellow", hi: "\u092a\u0940\u0932\u093e", hex: "#c8a335" },
  { key: "white", en: "White", hi: "\u0938\u092b\u0947\u0926", hex: "#d9dde4" },
  { key: "black", en: "Black", hi: "\u0915\u093e\u0932\u093e", hex: "#29354a" },
  { key: "purple", en: "Purple", hi: "\u092c\u0948\u0917\u0928\u0940", hex: "#5d4db0" },
  { key: "pink", en: "Pink", hi: "\u0917\u0941\u0932\u093e\u092c\u0940", hex: "#bb5a87" },
  { key: "gold", en: "Gold", hi: "\u0938\u0941\u0928\u0939\u0930\u093e", hex: "#b48d36" },
];

function resolveEnergyColorToken(fragment: string): EnergyColorToken | null {
  const value = repairDisplayText(String(fragment || "")).toLowerCase();
  if (!value) return null;

  if (value.includes("blue") || value.includes("नील")) return ENERGY_COLOR_LIBRARY[0];
  if (value.includes("green") || value.includes("हरा")) return ENERGY_COLOR_LIBRARY[1];
  if (value.includes("red") || value.includes("लाल")) return ENERGY_COLOR_LIBRARY[2];
  if (value.includes("orange") || value.includes("नारंगी")) return ENERGY_COLOR_LIBRARY[3];
  if (value.includes("yellow") || value.includes("पील")) return ENERGY_COLOR_LIBRARY[4];
  if (value.includes("white") || value.includes("सफेद")) return ENERGY_COLOR_LIBRARY[5];
  if (value.includes("black") || value.includes("काला")) return ENERGY_COLOR_LIBRARY[6];
  if (value.includes("purple") || value.includes("बैगनी")) return ENERGY_COLOR_LIBRARY[7];
  if (value.includes("pink") || value.includes("गुलाबी")) return ENERGY_COLOR_LIBRARY[8];
  if (value.includes("gold") || value.includes("सुनहरा")) return ENERGY_COLOR_LIBRARY[9];

  return null;
}

function buildEnergyPalette(rawColors: string[], fallbackText: string): EnergyColorToken[] {
  const bucket = new Map<string, EnergyColorToken>();

  const register = (token: EnergyColorToken | null) => {
    if (!token || bucket.has(token.key)) return;
    bucket.set(token.key, token);
  };

  const splitAndCollect = (source: string) => {
    const repaired = repairDisplayText(source);
    repaired
      .split(/[,/|]| and | & /gi)
      .map((part) => part.trim())
      .filter(Boolean)
      .forEach((part) => register(resolveEnergyColorToken(part)));
    register(resolveEnergyColorToken(repaired));
  };

  rawColors.forEach((item) => splitAndCollect(String(item || "")));
  if (!bucket.size) {
    splitAndCollect(fallbackText || "");
  }

  const result = Array.from(bucket.values()).slice(0, 3);
  return result.length ? result : [ENERGY_COLOR_LIBRARY[0], ENERGY_COLOR_LIBRARY[1]];
}

function getRemedyImage(remedy?: RemedyBundle | null) {
  const text = repairDisplayText(`${remedy?.anchor || ""} ${remedy?.mantra || ""}`).toLowerCase();
  if (text.includes("?????")) return ASSETS.deities.chandra;
  if (text.includes("???")) return ASSETS.deities.budh;
  if (text.includes("?????")) return ASSETS.deities.surya;
  if (text.includes("????") || text.includes("????????")) {
    return ASSETS.deities.guru;
  }
  if (text.includes("?????")) return ASSETS.deities.shukra;
  if (text.includes("???")) return ASSETS.deities.shani;
  if (text.includes("????")) return ASSETS.deities.rahu;
  if (text.includes("????")) return ASSETS.deities.ketu;
  if (text.includes("????")) return ASSETS.deities.mangal;
  return ASSETS.deities.chandra;
}

function numberClass(value?: number) {
  if (value === undefined) return "text-slate-600";
  if (value >= 75) return "text-emerald-700";
  if (value >= 50) return "text-amber-700";
  return "text-rose-700";
}

function getNumberImage(number?: number) {
  switch (number) {
    case 1:
      return ASSETS.deities.surya;
    case 2:
      return ASSETS.deities.chandra;
    case 3:
      return ASSETS.deities.guru;
    case 4:
      return ASSETS.deities.rahu;
    case 5:
      return ASSETS.deities.budh;
    case 6:
      return ASSETS.deities.shukra;
    case 7:
      return ASSETS.deities.ketu;
    case 8:
      return ASSETS.deities.shani;
    case 9:
      return ASSETS.deities.mangal;
    default:
      return ASSETS.chakra;
  }
}

function getCoverVisual(report: ReportResponse) {
  const mulank = getResolvedNumbers(report).mulank ?? 0;
  return mulank % 2 === 0 ? ASSETS.krishna : ASSETS.ganesha;
}

function getSectionAccent(section: HindiSection, report: ReportResponse) {
  const numbers = getResolvedNumbers(report);
  const repeating = report.content?.deterministic?.lo_shu?.repeating || [];

  switch (section.key) {
    case "profile":
    case "profile_snapshot":
      return { image: ASSETS.lotus, label: "Insight Signal (??????????? ?????)", note: "?? ????? ?? ????????? ???" };
    case "executive_summary":
      return { image: getNumberImage(numbers?.mulank), label: "Insight Signal (??????????? ?????)", note: "?????????? ?? ????? ?????" };
    case "core_numbers_analysis":
      return { image: getNumberImage(numbers?.bhagyank), label: "Insight Signal (??????????? ?????)", note: "????? ???????? ?? ??????" };
    case "mulank_description":
      return { image: getNumberImage(numbers?.mulank), label: "Insight Signal (??????????? ?????)", note: "????????? ??????????? ????" };
    case "bhagyank_description":
      return { image: getNumberImage(numbers?.bhagyank), label: "Insight Signal (??????????? ?????)", note: "???? ???? ?? ????? ?????" };
    case "name_number_analysis":
      return { image: getNumberImage(numbers?.name_energy), label: "Insight Signal (??????????? ?????)", note: "????? ?? ????? ??????" };
    case "number_interaction_analysis":
      return { image: ASSETS.chakra, label: "Insight Signal (??????????? ?????)", note: "???????? ??? ????? ???? ??? ???? ???" };
    case "loshu_grid_interpretation":
      return { image: ASSETS.mandala, label: "Insight Signal (??????????? ?????)", note: "??????? ?? ????????? ????? ?????" };
    case "missing_numbers_analysis":
      return { image: ASSETS.lotus, label: "Insight Signal (??????????? ?????)", note: "????? ????? ?? ?????????? ?????" };
    case "repeating_numbers_impact":
      return { image: getNumberImage(repeating[0]), label: "Insight Signal (??????????? ?????)", note: "?????? ?? ???????? ?? ??????" };
    case "mobile_number_numerology":
      return { image: getNumberImage(numbers?.mobile_total), label: "Insight Signal (??????????? ?????)", note: "?????? ???? ?? ??????" };
    case "mobile_life_number_compatibility":
      return { image: ASSETS.chakra, label: "Insight Signal (??????????? ?????)", note: "?????? ?? ???? ?? ??????" };
    case "personality_intelligence":
      return { image: ASSETS.lotus, label: "Insight Signal (??????????? ?????)", note: "??????? ?? ????? ?????" };
    case "current_problem_analysis":
      return { image: getCoverVisual(report), label: "Insight Signal (??????????? ?????)", note: "?????? ?????? ?? ?????????" };
    case "career_wealth_strategy":
      return { image: getNumberImage(numbers?.bhagyank), label: "Insight Signal (??????????? ?????)", note: "?? ?? ???????? ?? ??????" };
    case "relationship_patterns":
      return { image: getNumberImage(numbers?.mulank), label: "Insight Signal (??????????? ?????)", note: "????????? ???????? ?????" };
    case "health_signals":
      return { image: ASSETS.lotus, label: "Insight Signal (??????????? ?????)", note: "????????, ???? ?? ?????? ?????" };
    case "personal_year_forecast":
      return { image: getNumberImage(numbers?.personal_year), label: "Insight Signal (??????????? ?????)", note: "??????? ??????? ?????" };
    case "lucky_numbers":
      return { image: ASSETS.chakra, label: "Insight Signal (??????????? ?????)", note: "?????? ??????? ?? ???" };
    case "color_alignment":
      return { image: ASSETS.lotus, label: "Insight Signal (??????????? ?????)", note: "????? ?????? ?? ??? ??????????" };
    case "remedies_lifestyle_adjustments":
      return { image: getRemedyImage(report.content?.deterministic?.remedy), label: "Insight Signal (??????????? ?????)", note: "?????????? ????? ?? ???????" };
    case "strategic_growth_blueprint":
      return { image: ASSETS.om, label: "Insight Signal (??????????? ?????)", note: "????? ?????????? ?? ??????" };
    default:
      return { image: ASSETS.lotus, label: "Insight Signal (??????????? ?????)", note: "?? ?????? ?? ????????? ???" };
  }
}

function renderRichText(text: string) {
  const raw = repairDisplayText(String(text || ""));
  const parts = raw.split(/(\*\*.*?\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return <span key={`${part}-${index}`}>{part}</span>;
  });
}

function splitIntoColumns<T>(items: T[], columns: number) {
  if (!items.length || columns <= 1) return [items];
  const groups = Array.from({ length: columns }, () => [] as T[]);
  items.forEach((item, index) => {
    groups[index % columns].push(item);
  });
  return groups.filter((group) => group.length > 0);
}

function ReportPage({
  children,
  cover = false,
  pattern = "center",
  pageNumber,
  totalPages,
}: {
  children: ReactNode;
  cover?: boolean;
  pattern?: "center" | "top" | "bottom";
  pageNumber?: number;
  totalPages?: number;
}) {
  const baseMandalaClass = cover
    ? "absolute inset-0 h-full w-full object-cover scale-[1.08]"
    : "absolute inset-0 h-full w-full object-cover scale-[1.03]";

  const accentMandalaClass =
    pattern === "top"
      ? "absolute -right-10 -top-10 h-[88%] w-[88%] object-contain"
      : pattern === "bottom"
        ? "absolute -bottom-12 -left-10 h-[88%] w-[88%] object-contain"
        : "absolute inset-0 h-full w-full object-contain scale-[0.92]";

  return (
    <section
      className={cx(
        "report-page report-page--uniform relative overflow-hidden rounded-[28px] border border-[#c4a262]/70 bg-[linear-gradient(180deg,#fffdf8_0%,#f6efdf_100%)] p-5 shadow-[0_24px_70px_rgba(25,44,73,0.12)] print:min-h-0 print:rounded-none print:border-[#c4a262] print:p-4 print:shadow-none sm:p-8",
        `report-page--pattern-${pattern}`,
        cover && "report-page--cover",
      )}
    >
      <picture className={cx("report-page__mandala-picture pointer-events-none", baseMandalaClass)}>
        <img
          src={ASSETS.mandala}
          alt="Mandala background"
          loading="eager"
          decoding="sync"
          className="report-page__mandala-base h-full w-full object-cover"
        />
      </picture>
      <img
        src={ASSETS.mandala}
        alt=""
        aria-hidden="true"
        className={cx("report-page__mandala-accent pointer-events-none", accentMandalaClass)}
      />
      <div
        className={cx(
          "report-page__veil pointer-events-none absolute inset-0",
          cover ? "report-page__veil--cover" : "report-page__veil--section",
        )}
      />
      <div className="pointer-events-none absolute inset-[14px] rounded-[22px] border border-[#d8c49d]/60" />
      <div className="relative z-10">{children}</div>
      {pageNumber ? (
        <div className="report-page-number" aria-label={`Page ${pageNumber}`}>
          {totalPages ? `${pageNumber}/${totalPages}` : pageNumber}
        </div>
      ) : null}
    </section>
  );
}

function PageHeader({
  index,
  title,
  subtitle,
  accent,
}: {
  index: number;
  title: string;
  subtitle?: string;
  accent: { image: string; label: string; note: string };
}) {
  void index;
  void accent;
  const titleLines = String(title || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  return (
    <div className="report-page-header mb-6">
      <div className="max-w-3xl">
        <h2 className="font-[var(--font-report-heading)] text-3xl leading-tight text-[#173a63] sm:text-[2.35rem]">
          {titleLines.length
            ? titleLines.map((line, idx) => (
                <span
                  key={`${line}-${idx}`}
                  className={idx === 0 ? "block" : "mt-1 block text-[0.75em] font-semibold text-[#6f6253]"}
                >
                  {line}
                </span>
              ))
            : title}
        </h2>
        {subtitle ? (
          <p className="report-copy mt-2 max-w-2xl whitespace-pre-line text-sm leading-6 text-[#6f6253] sm:text-base">
            {repairDisplayText(subtitle)}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function InfoCard({
  title,
  lines = [],
  tone = "default",
  className,
  imageSrc,
  imageAlt,
}: {
  title: string;
  lines?: string[];
  tone?: "default" | "accent" | "soft";
  className?: string;
  imageSrc?: string;
  imageAlt?: string;
}) {
  void imageSrc;
  void imageAlt;
  const safeLines = Array.isArray(lines)
    ? lines
        .filter((line) => typeof line === "string" && line.trim().length > 0)
        .map((line) => String(line))
    : [];
  const displayLines = safeLines.length ? safeLines : ["Data not available."];
  return (
    <div
      className={cx(
        "report-info-card report-card--uniform rounded-[24px] border p-4 sm:p-5",
        tone === "accent" && "border-[#c09b57] bg-[linear-gradient(180deg,#fff7df_0%,#f6e8c5_100%)]",
        tone === "soft" && "border-[#d7c39d] bg-white/75",
        tone === "default" && "border-[#cfb584] bg-[#fffaf0]/92",
        className,
      )}
    >
      <div className="report-info-card__header mb-3 flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="report-info-card__title text-base font-semibold leading-6 text-[#173a63]">
            {repairDisplayText(title)}
          </p>
        </div>
      </div>
      <div className="report-info-card__content report-copy space-y-2.5 text-[15px] leading-[1.8] text-[#213f63]">
        {displayLines.map((line, idx) => {
          const item = parseLine(line);
          return (
            <div key={`${title}-${idx}`}>
              {item.label ? <span className="font-semibold text-[#173a63]">{item.label}: </span> : null}
              <span>{renderRichText(item.value || line)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MetricPill({
  label,
  value,
  valueClass,
  size = "default",
}: {
  label: string;
  value: string | number;
  valueClass?: string;
  size?: "default" | "cover";
}) {
  const coverMode = size === "cover";
  const valueText = String(value ?? "");
  const longValue = valueText.length >= 8;
  return (
    <div
      className={cx(
        "rounded-[20px] border border-[#d7c39d] bg-white/85 text-center print:rounded-[14px]",
        coverMode
          ? "min-h-[108px] px-5 py-5 print:min-h-[94px] print:px-3.5 print:py-3"
          : "px-4 py-3.5 print:px-2.5 print:py-2",
      )}
    >
      <p
        className={cx(
          "font-medium text-[#8c7652]",
          coverMode ? "text-[15px] leading-5 print:text-[13px]" : "text-sm leading-5 print:text-[11px] print:leading-4",
        )}
      >
        {label}
      </p>
      <p
        className={cx(
          "font-bold text-[#16375e]",
          coverMode
            ? longValue
              ? "mt-2 text-[30px] leading-tight print:text-[25px]"
              : "mt-2 text-[36px] leading-none print:text-[30px]"
            : "mt-2 text-2xl print:mt-1 print:text-xl",
          valueClass,
        )}
      >
        {value}
      </p>
    </div>
  );
}

function MetricRing({ label, value }: { label: string; value: number }) {
  const safeValue = Math.min(100, Math.max(0, value));
  return (
    <div className="report-metric-ring-card rounded-[18px] border border-[#d6bf91] bg-white/90 p-3 text-center">
      <p className="text-[15px] font-semibold text-[#173a63]">{repairDisplayText(label)}</p>
      <div
        className="report-metric-ring mx-auto mt-3 h-[124px] w-[124px] rounded-full p-[10px]"
        style={{
          background: `conic-gradient(#1f4a7a 0 ${safeValue}%, #c8a855 ${safeValue}% 100%)`,
        }}
      >
        <div className="flex h-full w-full items-center justify-center rounded-full bg-[#fffdf7] text-[44px] font-semibold leading-none text-[#173a63]">
          {safeValue}
        </div>
      </div>
    </div>
  );
}

function LifeIntelligenceBalance({
  metrics,
}: {
  metrics: Array<{ key: string; label: string; number: number }>;
}) {
  const leftMetric = metrics[0];
  const rightMetric = metrics[1];
  const leftLabel = repairDisplayText(String(leftMetric?.label || "Dharma Balance").replace(/\(.*?\)/g, "").trim());
  const rightLabel = repairDisplayText(String(rightMetric?.label || "Confidence").replace(/\(.*?\)/g, "").trim());
  const leftValue = leftMetric?.number ?? 0;
  const rightValue = rightMetric?.number ?? 0;

  const toMetricDisplay = (label: string) => {
    const cleaned = repairDisplayText(label).toLowerCase();
    if (cleaned.includes("????") || cleaned.includes("dharma")) {
      return { en: "Dharma Balance", hi: "???? ??????" };
    }
    if (cleaned.includes("???????????") || cleaned.includes("confidence")) {
      return { en: "Confidence", hi: "???? ???????" };
    }
    return { en: repairDisplayText(label), hi: "" };
  };

  const leftDisplay = toMetricDisplay(leftLabel);
  const rightDisplay = toMetricDisplay(rightLabel);

  return (
    <div className="life-intel-balance">
      <svg className="life-intel-balance__svg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
        <circle cx="50" cy="50" r="45.5" fill="none" stroke="#d8c79f" strokeOpacity="0.22" strokeWidth="0.34" />

        <path d="M50 8 L48.2 13.8 L50 19.6 L51.8 13.8 Z" fill="#fff1cd" stroke="#b08d48" strokeWidth="0.55" />
        <line x1="50" y1="19.6" x2="50" y2="28.8" stroke="#b08d48" strokeWidth="0.85" />

        <line x1="22" y1="40" x2="78" y2="30" stroke="#b08d48" strokeWidth="1.2" />
        <line x1="22" y1="41.2" x2="78" y2="31.2" stroke="#ead7a5" strokeWidth="0.48" />
        <circle cx="50" cy="35" r="3" fill="#f7e6bc" stroke="#b08d48" strokeWidth="0.6" />
        <circle cx="22" cy="40" r="1.35" fill="#f7e6bc" stroke="#b08d48" strokeWidth="0.5" />
        <circle cx="78" cy="30" r="1.35" fill="#f7e6bc" stroke="#b08d48" strokeWidth="0.5" />

        <line x1="50" y1="38.2" x2="50" y2="80" stroke="#b08d48" strokeWidth="1.28" />
        <line x1="51.1" y1="38.2" x2="51.1" y2="80" stroke="#ead7a5" strokeWidth="0.4" />
        <rect x="47.1" y="80" width="5.8" height="8.8" rx="1.4" fill="#f8f0db" stroke="#c8aa67" strokeWidth="0.6" />
        <path d="M39 89 Q50 84.6 61 89" fill="none" stroke="#b08d48" strokeWidth="1.04" />
        <path d="M39 89.8 L61 89.8" fill="none" stroke="#d8be83" strokeWidth="0.5" />

        <line x1="22" y1="40" x2="16.8" y2="57" stroke="#c29e58" strokeWidth="0.68" />
        <line x1="22" y1="40" x2="27.2" y2="57" stroke="#c29e58" strokeWidth="0.68" />
        <line x1="78" y1="30" x2="72.8" y2="53" stroke="#c29e58" strokeWidth="0.68" />
        <line x1="78" y1="30" x2="83.2" y2="53" stroke="#c29e58" strokeWidth="0.68" />

        <path d="M12.8 57 Q22 66 31.2 57" fill="none" stroke="#b08d48" strokeWidth="0.95" />
        <path d="M68.8 53 Q78 62 87.2 53" fill="none" stroke="#b08d48" strokeWidth="0.95" />
        <path d="M14 57.5 Q22 63.6 30 57.5" fill="none" stroke="#ead7a5" strokeWidth="0.45" />
        <path d="M70 53.5 Q78 59.6 86 53.5" fill="none" stroke="#ead7a5" strokeWidth="0.45" />
      </svg>

      <div className="life-intel-orb life-intel-orb--gold">
        <p className="life-intel-orb__label">{leftDisplay.en}</p>
        <p className="life-intel-orb__value">{leftValue}</p>
        {leftDisplay.hi ? <p className="life-intel-orb__hi">({leftDisplay.hi})</p> : null}
      </div>
      <div className="life-intel-orb life-intel-orb--silver">
        <p className="life-intel-orb__label">{rightDisplay.en}</p>
        <p className="life-intel-orb__value">{rightValue}</p>
        {rightDisplay.hi ? <p className="life-intel-orb__hi">({rightDisplay.hi})</p> : null}
      </div>
    </div>
  );
}

function StrategicOverviewVisual({
  report,
  title,
  value,
}: {
  report: ReportResponse;
  title: string;
  value: string;
}) {
  const numbers = getResolvedNumbers(report);
  const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
  const pyth = (deterministic.numerologyValues?.pythagorean || {}) as Record<string, any>;
  const leftA = numbers.mulank ?? toNumber(pyth.life_path_number) ?? "--";
  const leftB = numbers.bhagyank ?? toNumber(pyth.destiny_number) ?? "--";
  const badgeValueRaw = repairDisplayText(value);
  const badgeValueLower = badgeValueRaw.toLowerCase();
  const badgeHindiValue = /[\u0900-\u097f]/.test(badgeValueRaw)
    ? badgeValueRaw
    : badgeValueLower.includes("support")
      ? "?????"
      : badgeValueLower.includes("challeng")
        ? "???????????"
        : badgeValueLower.includes("neutral") || badgeValueLower.includes("balanced")
          ? "???????"
          : "?????";
  const badgeEnglish = `${repairDisplayText(title)}: ${badgeValueRaw || "Supportive"}`;
  const badgeHindi = `?????? ?????????????: ${badgeHindiValue}`;

  return (
    <div className="strategic-hero rounded-[24px] border border-[#c8aa66] bg-white/88 p-4">
      <img src={ASSETS.mandala} alt="" aria-hidden="true" loading="lazy" decoding="async" className="strategic-hero__bg" />
      <div className="strategic-hero__badge">
        <p className="strategic-hero__badge-en">{badgeEnglish}</p>
        <p className="strategic-hero__badge-hi">{badgeHindi}</p>
      </div>

      <div className="strategic-hero__canvas">
        <svg className="strategic-hero__svg" viewBox="0 0 1000 430" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
          <defs>
            <linearGradient id="strategicGoldFlow" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#fff1c8" />
              <stop offset="42%" stopColor="#ddb969" />
              <stop offset="100%" stopColor="#af7f3e" />
            </linearGradient>
            <linearGradient id="strategicBlueFlow" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#9be8ff" />
              <stop offset="45%" stopColor="#2f9ce6" />
              <stop offset="100%" stopColor="#173a67" />
            </linearGradient>
            <radialGradient id="strategicNodeGold" cx="35%" cy="30%">
              <stop offset="0%" stopColor="#fff8df" />
              <stop offset="54%" stopColor="#efcf80" />
              <stop offset="100%" stopColor="#c59648" />
            </radialGradient>
            <radialGradient id="strategicNodeGlow" cx="50%" cy="50%">
              <stop offset="0%" stopColor="rgba(255,234,168,0.62)" />
              <stop offset="68%" stopColor="rgba(240,201,111,0.24)" />
              <stop offset="100%" stopColor="rgba(0,0,0,0)" />
            </radialGradient>
            <radialGradient id="strategicHeroGlow" cx="58%" cy="52%">
              <stop offset="0%" stopColor="rgba(92,184,255,0.42)" />
              <stop offset="45%" stopColor="rgba(25,74,124,0.22)" />
              <stop offset="100%" stopColor="rgba(0,0,0,0)" />
            </radialGradient>
            <linearGradient id="strategicDarkBand" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="rgba(19,43,72,0)" />
              <stop offset="16%" stopColor="rgba(19,43,72,0.24)" />
              <stop offset="52%" stopColor="rgba(19,43,72,0.52)" />
              <stop offset="86%" stopColor="rgba(19,43,72,0.2)" />
              <stop offset="100%" stopColor="rgba(19,43,72,0)" />
            </linearGradient>
            <filter id="strategicSoftGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="8" />
            </filter>
            <filter id="strategicHardGlow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="3.2" />
            </filter>
          </defs>

          <rect x="0" y="0" width="1000" height="430" fill="url(#strategicHeroGlow)" />
          <ellipse cx="615" cy="218" rx="440" ry="126" fill="url(#strategicDarkBand)" />
          <ellipse cx="615" cy="218" rx="358" ry="98" fill="url(#strategicHeroGlow)" opacity="0.55" />

          <circle cx="88" cy="130" r="92" fill="url(#strategicNodeGlow)" filter="url(#strategicSoftGlow)" />
          <circle cx="88" cy="300" r="92" fill="url(#strategicNodeGlow)" filter="url(#strategicSoftGlow)" />
          <circle cx="88" cy="130" r="41" fill="url(#strategicNodeGold)" stroke="#c7a35d" strokeWidth="3.4" />
          <circle cx="88" cy="300" r="41" fill="url(#strategicNodeGold)" stroke="#c7a35d" strokeWidth="3.4" />
          <circle cx="88" cy="130" r="54" fill="none" stroke="#f7e7bf" strokeWidth="2.2" opacity="0.84" />
          <circle cx="88" cy="300" r="54" fill="none" stroke="#f7e7bf" strokeWidth="2.2" opacity="0.84" />
          <text x="88" y="144" textAnchor="middle" fontFamily="Georgia, serif" fontSize="43" fontWeight="700" fill="#173b66">
            {leftA}
          </text>
          <text x="88" y="314" textAnchor="middle" fontFamily="Georgia, serif" fontSize="43" fontWeight="700" fill="#173b66">
            {leftB}
          </text>

          <path d="M138 130 C248 134 286 176 420 202" stroke="url(#strategicBlueFlow)" strokeWidth="11.8" fill="none" filter="url(#strategicHardGlow)" />
          <path d="M138 300 C248 296 286 254 420 228" stroke="url(#strategicBlueFlow)" strokeWidth="11.8" fill="none" filter="url(#strategicHardGlow)" />
          <path d="M138 130 C248 134 286 176 420 202" stroke="url(#strategicGoldFlow)" strokeWidth="4.1" fill="none" opacity="0.9" />
          <path d="M138 300 C248 296 286 254 420 228" stroke="url(#strategicGoldFlow)" strokeWidth="4.1" fill="none" opacity="0.9" />
          <path d="M138 128 C226 144 266 184 420 208" stroke="#8fe8ff" strokeWidth="4.7" fill="none" opacity="0.78" />
          <path d="M138 302 C226 286 266 246 420 222" stroke="#8fe8ff" strokeWidth="4.7" fill="none" opacity="0.78" />
          <path d="M140 126 C235 138 272 176 420 198" stroke="#c5f5ff" strokeWidth="2.2" fill="none" opacity="0.78" />
          <path d="M140 304 C235 292 272 254 420 232" stroke="#c5f5ff" strokeWidth="2.2" fill="none" opacity="0.78" />

          <circle cx="194" cy="143" r="2.8" fill="#f4d68b" opacity="0.9" />
          <circle cx="246" cy="170" r="2.6" fill="#f4d68b" opacity="0.9" />
          <circle cx="280" cy="186" r="2.4" fill="#f4d68b" opacity="0.88" />
          <circle cx="194" cy="286" r="2.8" fill="#f4d68b" opacity="0.9" />
          <circle cx="246" cy="259" r="2.6" fill="#f4d68b" opacity="0.9" />
          <circle cx="280" cy="243" r="2.4" fill="#f4d68b" opacity="0.88" />

          <rect x="432" y="138" width="102" height="170" rx="21" fill="rgba(255,255,255,0.76)" stroke="#ba975b" strokeWidth="3.1" />
          <rect x="452" y="164" width="62" height="116" rx="11" fill="rgba(26,70,117,0.2)" />
          <polygon points="452,280 514,164 514,280" fill="rgba(255,255,255,0.12)" />
          <line x1="471" y1="152" x2="493" y2="152" stroke="#ba975b" strokeWidth="3" strokeLinecap="round" />
          <circle cx="483" cy="292" r="6.4" fill="none" stroke="#ba975b" strokeWidth="2.3" />

          <ellipse cx="726" cy="218" rx="268" ry="126" fill="url(#strategicHeroGlow)" opacity="0.92" />
          <line x1="548" y1="218" x2="920" y2="218" stroke="url(#strategicBlueFlow)" strokeWidth="8.5" strokeLinecap="round" filter="url(#strategicHardGlow)" />
          <line x1="548" y1="218" x2="920" y2="218" stroke="url(#strategicGoldFlow)" strokeWidth="2.2" strokeLinecap="round" opacity="0.8" />
          <line x1="568" y1="218" x2="568" y2="210" stroke="#f4d68b" strokeWidth="3.2" />
          <line x1="592" y1="218" x2="592" y2="202" stroke="#f4d68b" strokeWidth="3.1" />
          <line x1="616" y1="218" x2="616" y2="188" stroke="#f4d68b" strokeWidth="3" />
          <line x1="640" y1="218" x2="640" y2="173" stroke="#f4d68b" strokeWidth="2.95" />
          <line x1="664" y1="218" x2="664" y2="154" stroke="#f4d68b" strokeWidth="2.9" />
          <line x1="688" y1="218" x2="688" y2="137" stroke="#f4d68b" strokeWidth="2.8" />
          <line x1="712" y1="218" x2="712" y2="128" stroke="#f4d68b" strokeWidth="2.8" />
          <line x1="736" y1="218" x2="736" y2="137" stroke="#f4d68b" strokeWidth="2.8" />
          <line x1="760" y1="218" x2="760" y2="154" stroke="#f4d68b" strokeWidth="2.9" />
          <line x1="784" y1="218" x2="784" y2="173" stroke="#f4d68b" strokeWidth="2.95" />
          <line x1="808" y1="218" x2="808" y2="188" stroke="#f4d68b" strokeWidth="3" />
          <line x1="832" y1="218" x2="832" y2="202" stroke="#f4d68b" strokeWidth="3.1" />
          <line x1="856" y1="218" x2="856" y2="210" stroke="#f4d68b" strokeWidth="3.2" />

        </svg>
      </div>
    </div>
  );
}

function FocusInsightsVisual({
  focusText,
}: {
  focusText: string;
}) {
  const resolvedFocus = repairDisplayText(focusText || "General Alignment");
  return (
    <div className="focus-insights-visual rounded-[24px] border border-[#c8aa66] bg-white/88 p-4">
      <img src={ASSETS.mandala} alt="" aria-hidden="true" loading="lazy" decoding="async" className="focus-insights-visual__bg" />

      <div className="focus-insights-wheel" aria-hidden="true">
        <svg viewBox="0 0 420 300" className="focus-insights-wheel__svg">
          <defs>
            <radialGradient id="focusGold" cx="34%" cy="30%" r="76%">
              <stop offset="0%" stopColor="#fff7d8" />
              <stop offset="46%" stopColor="#e7c978" />
              <stop offset="100%" stopColor="#bd923f" />
            </radialGradient>
            <radialGradient id="focusGlow" cx="50%" cy="50%" r="60%">
              <stop offset="0%" stopColor="rgba(245,217,145,0.7)" />
              <stop offset="100%" stopColor="rgba(245,217,145,0)" />
            </radialGradient>
          </defs>

          <circle cx="138" cy="164" r="102" fill="none" stroke="#c39a4e" strokeWidth="3" />
          <circle cx="138" cy="164" r="78" fill="none" stroke="#c9aa66" strokeWidth="2.4" />
          <circle cx="138" cy="164" r="54" fill="none" stroke="#c9aa66" strokeWidth="2" />
          <circle cx="138" cy="164" r="30" fill="none" stroke="#c9aa66" strokeWidth="1.8" />
          {Array.from({ length: 12 }).map((_, idx) => {
            const angle = (Math.PI * 2 * idx) / 12;
            const x2 = 138 + Math.cos(angle) * 102;
            const y2 = 164 + Math.sin(angle) * 102;
            return <line key={`focus-spoke-${idx}`} x1="138" y1="164" x2={x2} y2={y2} stroke="#c8a55f" strokeWidth="1.6" />;
          })}

          <path d="M138 164 L236 128 A102 102 0 0 1 240 164 Z" fill="url(#focusGold)" opacity="0.96" />
          <ellipse cx="228" cy="144" rx="36" ry="26" fill="url(#focusGlow)" opacity="0.8" />
          <line x1="226" y1="145" x2="292" y2="145" stroke="#c8a55f" strokeWidth="2.2" />
        </svg>
      </div>

      <div className="focus-insights-callout">
        <p className="focus-insights-callout__en">Focus Area: {resolvedFocus}</p>
        <p className="focus-insights-callout__hi">????? ???????: {resolvedFocus}</p>
      </div>
    </div>
  );
}

function FavorableTimingVisual({
  highlightedNodes,
}: {
  highlightedNodes: Array<string | number>;
}) {
  const nodes = highlightedNodes.slice(0, 3).map((n) => String(n));
  const displayNodes = nodes.length ? nodes : ["1", "4", "6"];
  return (
    <div className="fav-timing-visual rounded-[24px] border border-[#c8aa66] bg-white/88 p-4">
      <img src={ASSETS.mandala} alt="" aria-hidden="true" loading="lazy" decoding="async" className="fav-timing-visual__bg" />

      <div className="fav-timing-cubes" aria-hidden="true">
        <svg viewBox="0 0 420 300" className="fav-timing-cubes__svg">
          <defs>
            <linearGradient id="favCubeFace" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#f5db9a" />
              <stop offset="100%" stopColor="#b78637" />
            </linearGradient>
            <linearGradient id="favCubeTop" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#fff2cd" />
              <stop offset="100%" stopColor="#e3bf72" />
            </linearGradient>
            <filter id="favSoftGlow">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <rect x="58" y="136" width="116" height="116" rx="8" fill="url(#favCubeFace)" stroke="#a77932" strokeWidth="2.2" />
          <polygon points="58,136 92,112 208,112 174,136" fill="url(#favCubeTop)" stroke="#a77932" strokeWidth="2.2" />
          <polygon points="174,136 208,112 208,228 174,252" fill="#c89b4a" stroke="#a77932" strokeWidth="2.2" />

          <rect x="112" y="64" width="116" height="116" rx="8" fill="url(#favCubeFace)" stroke="#a77932" strokeWidth="2.2" />
          <polygon points="112,64 146,40 262,40 228,64" fill="url(#favCubeTop)" stroke="#a77932" strokeWidth="2.2" />
          <polygon points="228,64 262,40 262,156 228,180" fill="#c89b4a" stroke="#a77932" strokeWidth="2.2" />

          <rect x="224" y="136" width="116" height="116" rx="8" fill="url(#favCubeFace)" stroke="#a77932" strokeWidth="2.2" />
          <polygon points="224,136 258,112 374,112 340,136" fill="url(#favCubeTop)" stroke="#a77932" strokeWidth="2.2" />
          <polygon points="340,136 374,112 374,228 340,252" fill="#c89b4a" stroke="#a77932" strokeWidth="2.2" />

          <circle cx="170" cy="96" r="30" fill="rgba(255,232,162,0.5)" filter="url(#favSoftGlow)" />
          <circle cx="116" cy="168" r="30" fill="rgba(255,232,162,0.5)" filter="url(#favSoftGlow)" />
          <circle cx="284" cy="168" r="30" fill="rgba(255,232,162,0.5)" filter="url(#favSoftGlow)" />

          <text x="170" y="106" textAnchor="middle" fontFamily="Georgia, serif" fontSize="48" fontWeight="700" fill="#16375f">
            {displayNodes[0]}
          </text>
          <text x="116" y="178" textAnchor="middle" fontFamily="Georgia, serif" fontSize="48" fontWeight="700" fill="#16375f">
            {displayNodes[1] || displayNodes[0]}
          </text>
          <text x="284" y="178" textAnchor="middle" fontFamily="Georgia, serif" fontSize="48" fontWeight="700" fill="#16375f">
            {displayNodes[2] || displayNodes[1] || displayNodes[0]}
          </text>
        </svg>
      </div>

      <div className="fav-timing-callout">
        <p className="fav-timing-callout__en">Highlighted Timing Nodes: {displayNodes.join(", ")}</p>
        <p className="fav-timing-callout__hi">??? ???????: {displayNodes.join(", ")}</p>
      </div>
    </div>
  );
}

function EnergyAlignmentVisual({
  palette,
}: {
  palette: EnergyColorToken[];
}) {
  const resolved = palette.length ? palette : [ENERGY_COLOR_LIBRARY[0], ENERGY_COLOR_LIBRARY[1]];
  const topColor = resolved[0];
  const bottomColor = resolved[1] || resolved[0];
  const accentColor = resolved[2] || resolved[1] || resolved[0];
  const englishLine = resolved.map((item) => item.en).join(", ");
  const hindiLine = resolved.map((item) => item.hi).join(", ");

  return (
    <div className="energy-align-visual rounded-[24px] border border-[#c8aa66] p-4">
      <img src={ASSETS.mandala} alt="" aria-hidden="true" loading="lazy" decoding="async" className="energy-align-visual__bg" />
      <div
        className="energy-align-visual__split"
        style={{
          background: `linear-gradient(180deg, ${topColor.hex} 0%, ${topColor.hex} 50%, ${bottomColor.hex} 50%, ${bottomColor.hex} 100%)`,
        }}
      />
      <div
        className="energy-align-visual__pulse"
        style={{
          background: `radial-gradient(circle at 66% 46%, ${accentColor.hex}66 0%, ${accentColor.hex}00 64%)`,
        }}
      />

      <div className="energy-align-visual__content">
        <p className="energy-align-visual__kicker">Key Colors:</p>
        <p className="energy-align-visual__english">{englishLine}</p>
        <p className="energy-align-visual__hindi">{hindiLine}</p>

        <div className="energy-align-visual__swatches" aria-label="Energy colors">
          {resolved.map((item) => (
            <div key={`energy-chip-${item.key}`} className="energy-align-visual__swatch">
              <span className="energy-align-visual__swatch-dot" style={{ backgroundColor: item.hex }} />
              <span className="energy-align-visual__swatch-label">{item.en}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ProfilePentagonSummary({ report, keyTraits }: { report: ReportResponse; keyTraits?: string }) {
  const numbers = getResolvedNumbers(report);
  const fullName = resolveReportName(report) || "AnkAI User";
  const nameLines = fullName.split(/\s+/).slice(0, 2);
  const nodes = [
    {
      key: "mulank",
      label: "Mulank",
      value: numbers.mulank ?? "--",
      x: 50,
      y: 17,
      labelX: 50,
      labelY: 6,
    },
    {
      key: "bhagyank",
      label: "Bhagyank",
      value: numbers.bhagyank ?? "--",
      x: 76,
      y: 40,
      labelX: 84,
      labelY: 40,
    },
    {
      key: "name_energy",
      label: "Name Energy",
      value: numbers.name_energy ?? "--",
      x: 66,
      y: 73,
      labelX: 72,
      labelY: 88,
    },
    {
      key: "email_energy",
      label: "Email Energy",
      value: numbers.email_energy ?? "--",
      x: 34,
      y: 73,
      labelX: 28,
      labelY: 88,
    },
    {
      key: "mobile_total",
      label: "Mobile Energy",
      value: numbers.mobile_total ?? "--",
      x: 24,
      y: 40,
      labelX: 16,
      labelY: 40,
    },
  ] as const;
  const pathOrder = [0, 1, 2, 3, 4, 0];

  return (
    <div className="profile-pentagon-card self-start rounded-[22px] border border-[#c9aa66] bg-white/94 p-3">
      <div className="profile-pentagon-wrap relative overflow-visible">
        <img
          src={ASSETS.mandala}
          alt=""
          aria-hidden="true"
          loading="lazy"
          decoding="async"
          className="profile-pentagon-bg pointer-events-none absolute inset-0 h-full w-full object-contain"
        />
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
          <circle cx="50" cy="50" r="35" fill="none" stroke="#dcc691" strokeOpacity="0.28" strokeWidth="0.35" />
          {pathOrder.slice(0, -1).map((nodeIndex, idx) => {
            const from = nodes[nodeIndex];
            const to = nodes[pathOrder[idx + 1]];
            return (
              <g key={`${from.key}-${to.key}`}>
                <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#f8efda" strokeWidth="1.0" strokeOpacity="0.95" />
                <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#c7a55a" strokeWidth="0.55" strokeOpacity="0.85" />
              </g>
            );
          })}
          {nodes.map((node) => (
            <g key={`center-${node.key}`}>
              <line x1={50} y1={50} x2={node.x} y2={node.y} stroke="#f8efda" strokeWidth="0.7" strokeOpacity="0.8" />
              <line x1={50} y1={50} x2={node.x} y2={node.y} stroke="#d2b06a" strokeWidth="0.36" strokeOpacity="0.62" />
            </g>
          ))}
        </svg>

        {nodes.map((node) => (
          <div key={node.key} className="profile-p-node absolute" style={{ left: `${node.x}%`, top: `${node.y}%` }}>
            <div className="profile-p-dot" />
          </div>
        ))}

        {nodes.map((node) => (
          <div
            key={`${node.key}-label`}
            className="profile-p-label absolute text-center"
            style={{
              left: `${node.labelX}%`,
              top: `${node.labelY}%`,
              transform: "translate(-50%, -50%)",
            }}
          >
            <span className="profile-p-label__name">{node.label}</span>
            <span className="profile-p-label__value">{node.value}</span>
          </div>
        ))}

        <div className="profile-p-center absolute left-1/2 top-1/2">
          <div className="profile-p-center-inner">
            {nameLines.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
        </div>
      </div>

      <div className="profile-p-traits mt-2 rounded-[12px] border border-[#dcc695] bg-[#fffaf0] px-3 py-2 text-sm text-[#1f3f65]">
        <span className="font-semibold text-[#173a63]">Key Traits: </span>
        {keyTraits || "--"}
      </div>
    </div>
  );
}

function NumberDynamicsVisual({
  report,
  comboNumbers,
  missingNumbers,
}: {
  report: ReportResponse;
  comboNumbers: Array<string | number>;
  missingNumbers: Array<string | number>;
}) {
  void report;
  return (
    <div className="number-dyn-visual rounded-[24px] border border-[#c8aa66] bg-white/88 p-4">
      <img src={ASSETS.mandala} alt="" aria-hidden="true" loading="lazy" decoding="async" className="number-dyn-visual__bg" />

      <div className="number-dyn-cube-block">
        <p className="number-dyn-cube-title">Core Combo</p>
        <div className="number-dyn-cube-grid number-dyn-cube-grid--core">
          {comboNumbers.slice(0, 3).map((num, idx) => (
            <span key={`combo-${idx}`} className={cx("number-dyn-cube", `number-dyn-cube--tone-${(idx % 3) + 1}`)}>
              {num}
            </span>
          ))}
        </div>
        <p className="number-dyn-cube-caption">Core Combo {comboNumbers.join(", ")}</p>
      </div>

      <div className="number-dyn-cube-block">
        <p className="number-dyn-cube-title number-dyn-cube-title--muted">Missing Numbers</p>
        <div className="number-dyn-cube-grid number-dyn-cube-grid--missing">
          {missingNumbers.slice(0, 6).map((num, idx) => (
            <span key={`missing-${idx}`} className="number-dyn-cube number-dyn-cube--muted">
              {num}
            </span>
          ))}
        </div>
        <p className="number-dyn-cube-caption number-dyn-cube-caption--muted">Missing {missingNumbers.join(", ")}</p>
      </div>
    </div>
  );
}

function CoreNumerologyPillarsVisual({ report }: { report: ReportResponse }) {
  const numbers = getResolvedNumbers(report);
  const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
  const pyth = (deterministic.numerologyValues?.pythagorean || {}) as Record<string, any>;

  const lifePath = toNumber(pyth.life_path_number) ?? numbers.bhagyank ?? "--";
  const destiny = toNumber(pyth.destiny_number) ?? numbers.mulank ?? "--";
  const expression = toNumber(pyth.expression_number) ?? "--";

  const pillars = [
    { key: "life_path", label: "Life Path", value: lifePath },
    { key: "destiny", label: "Destiny", value: destiny },
    { key: "expression", label: "Expression", value: expression },
  ] as const;

  return (
    <div className="core-pillars rounded-[24px] border border-[#c8aa66] bg-white/88 p-4">
      <img src={ASSETS.mandala} alt="" aria-hidden="true" loading="lazy" decoding="async" className="core-pillars__bg" />
      <div className="core-pillars__header">Core Numerology</div>

      <div className="core-pillars__canvas">
        <div className="core-pillars__network" aria-hidden="true">
          <span className="core-pillars__line core-pillars__line--h1" />
          <span className="core-pillars__line core-pillars__line--h2" />
          <span className="core-pillars__line core-pillars__line--v1" />
          <span className="core-pillars__line core-pillars__line--v2" />
          <span className="core-pillars__dot core-pillars__dot--a" />
          <span className="core-pillars__dot core-pillars__dot--b" />
          <span className="core-pillars__dot core-pillars__dot--c" />
          <span className="core-pillars__dot core-pillars__dot--d" />
        </div>

        <div className="core-pillars__columns">
          {pillars.map((pillar) => (
            <div key={pillar.key} className="core-pillars__column">
              <div className="core-pillars__cap" />
              <div className="core-pillars__shaft">
                <span className="core-pillars__label">
                  {pillar.label} | {pillar.value}
                </span>
              </div>
              <div className="core-pillars__base" />
            </div>
          ))}
        </div>

        <div className="core-pillars__platform" aria-hidden="true" />
      </div>
    </div>
  );
}

function HighlightStrip({ text }: { text: string }) {
  const item = parseLine(text);
  return (
    <div className="report-copy rounded-[20px] border border-[#c6a05b] bg-[linear-gradient(90deg,#fff3d2_0%,#fbf4e5_100%)] px-5 py-4 text-[15px] leading-[1.8] text-[#214266]">
      {item.label ? <span className="font-semibold text-[#173a63]">{item.label}: </span> : null}
      <span>{item.value || text.replace(/\*\*/g, "")}</span>
    </div>
  );
}

function LoShuGridCard({ loShu, languageMode }: { loShu?: LoShuGrid; languageMode?: string }) {
  const counts = loShu?.grid_counts || {};
  const resolvedLanguage = String(languageMode || "").trim().toLowerCase();
  const labelsByLanguage: Record<string, { present: string; missing: string; countPrefix: string }> = {
    hindi: { present: "मौजूद", missing: "अनुपस्थित", countPrefix: "x" },
    english: { present: "Present", missing: "Missing", countPrefix: "x" },
    bilingual: { present: "मौजूद (Present)", missing: "अनुपस्थित (Missing)", countPrefix: "x" },
    hinglish: { present: "Maujood", missing: "Anupasthit", countPrefix: "x" },
  };
  const labels = labelsByLanguage[resolvedLanguage] || labelsByLanguage.hindi;

  return (
    <div className="grid grid-cols-3 gap-3 rounded-[24px] border border-[#cfb47c] bg-white/85 p-4">
      {LOSHU_LAYOUT.flat().map((number) => {
        const count = counts[String(number)] || 0;
        const missing = count === 0;
        const statusLabel = missing ? labels.missing : `${labels.present} ${labels.countPrefix}${count}`;
        return (
          <div
            key={number}
            className={cx(
              "flex min-h-[92px] flex-col items-center justify-center rounded-[20px] border p-3 text-center",
              missing ? "border-[#d8a4a4] bg-[#fbebeb]" : "border-[#bfd0e5] bg-[#eef5ff]",
            )}
          >
            <span className="text-3xl font-bold text-[#173a63]">{number}</span>
            <span className="report-copy mt-2 text-xs text-[#866d4c]">{statusLabel}</span>
          </div>
        );
      })}
    </div>
  );
}
function ValueTiles({
  title,
  values,
  tone = "soft",
  imageSrc,
}: {
  title: string;
  values: Array<string | number>;
  tone?: "accent" | "soft";
  imageSrc?: string;
}) {
  return (
    <div
      className={cx(
        "rounded-[24px] border p-4 sm:p-5",
        tone === "accent" ? "border-[#c09b57] bg-[linear-gradient(180deg,#fff7df_0%,#f6e8c5_100%)]" : "border-[#d7c39d] bg-white/75",
      )}
    >
      <div className="mb-4 flex items-center gap-3">
        {imageSrc ? (
          <span className="report-icon-badge h-11 w-11 flex-none">
            <img src={imageSrc} alt={title} loading="lazy" decoding="async" className="h-7 w-7 object-contain opacity-90" />
          </span>
        ) : null}
        <p className="text-base font-semibold leading-6 text-[#173a63]">{title}</p>
      </div>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
        {values.length ? (
          values.map((value, idx) => (
            <div
              key={`${title}-${value}-${idx}`}
              className="report-tile-value rounded-[16px] border border-[#d4c09a] bg-white/90 px-3 py-3 text-center text-lg font-semibold text-[#173a63]"
            >
              {value}
            </div>
          ))
        ) : (
          <div className="report-copy col-span-full rounded-[16px] border border-dashed border-[#d4c09a] px-3 py-3 text-center text-sm text-[#6f6253]">
            ???? ????? ?? ?
          </div>
        )}
      </div>
    </div>
  );
}

function ColorSwatches({ colors }: { colors: string[] }) {
  if (!colors.length) return null;

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {colors.map((color) => (
        <div key={color} className="rounded-[20px] border border-[#d4c09a] bg-white/80 p-3">
          <div className="h-16 rounded-[14px] border border-white/70" style={{ backgroundColor: swatchColor(color) }} />
          <p className="mt-3 text-sm font-semibold text-[#173a63]">{color}</p>
        </div>
      ))}
    </div>
  );
}

function CompatibilityMeter({ compatibility }: { compatibility?: CompatibilityBundle }) {
  const score = compatibility?.score ?? 0;

  return (
    <div className="rounded-[22px] border border-[#cfb47c] bg-white/80 p-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-[#9c7941]">
            ???? ??
          </p>
          <p className="mt-2 text-3xl font-bold text-[#173a63]">{score}/100</p>
          <p className="mt-1 text-sm text-[#6e6558]">{compatibility?.label || "?????"}</p>
        </div>
        <img src={ASSETS.chakra} alt="Chakra" loading="lazy" decoding="async" className="h-14 w-14 opacity-80" />
      </div>
      <div className="mt-4 h-3 overflow-hidden rounded-full bg-[#e8dcc5]">
        <div
          className="h-full rounded-full bg-[linear-gradient(90deg,#c39b54_0%,#1d4a78_100%)]"
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
    </div>
  );
}

function CoverPage({ report, pageNumber, totalPages }: { report: ReportResponse; pageNumber: number; totalPages: number }) {
  const legacyInput: InputNormalized = report.content?.input_normalized || {};
  const canonicalInput = report.content?.normalizedInput || {};
  const llmOnly = Boolean(
    (report as any)?.content?.meta?.llm_only ||
      (report as any)?.content?.meta?.llmOnly ||
      (report as any)?.content?.llm_only,
  );
  const languageMode = String(
    report?.content?.meta?.language ||
      report?.content?.normalizedInput?.language ||
      report?.content?.input_normalized?.language ||
      report?.content?.deterministic?.normalizedInput?.language ||
      "hindi",
  ).toLowerCase();
  const canonicalBirthCity = String(canonicalInput.city || "").trim();
  const resolvedBirthPlace =
    legacyInput.birth_place ||
    (canonicalBirthCity
      ? [canonicalInput.city, canonicalInput.country].filter((value) => String(value || "").trim()).join(", ")
      : "");
  const input: InputNormalized = {
    ...legacyInput,
    name: legacyInput.name || canonicalInput.fullName,
    date_of_birth: legacyInput.date_of_birth || canonicalInput.dateOfBirth,
    gender: legacyInput.gender || canonicalInput.gender,
    mobile: legacyInput.mobile || canonicalInput.mobileNumber,
    email: legacyInput.email || canonicalInput.email,
    current_problem: legacyInput.current_problem || canonicalInput.currentProblem || canonicalInput.focusArea,
    birth_place: resolvedBirthPlace,
  };
  const metrics: CoreMetrics | undefined = report.content?.core_metrics;
  const numbers = getResolvedNumbers(report);
  const coverVisual = ASSETS.krishna;

  return (
    <ReportPage cover pageNumber={pageNumber} totalPages={totalPages}>
      <div className="report-cover-layout flex min-h-[268mm] flex-col print:min-h-[258mm]">
      <div className="report-cover-main grid items-start gap-4 print:gap-3 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <div className="mt-3 flex justify-center print:mt-2">
            <img
              src={coverVisual}
              alt="Lord Krishna"
              loading="eager"
              decoding="sync"
              className="max-h-[250px] w-auto rounded-[24px] border border-[#d6c092] bg-white/70 p-2.5 shadow-[0_20px_52px_rgba(17,41,67,0.12)] print:max-h-[205px]"
            />
          </div>

          <p className="report-kicker mt-5 text-center text-xs font-semibold text-[#a27e43] print:mt-3">
            Strategic Intelligence Report
          </p>
          <h1 className="mt-3 text-center font-[var(--font-report-heading)] text-4xl leading-tight text-[#173a63] print:text-[2.85rem] sm:text-[3.65rem]">
            Life Signify Ank(अंक) AI
          </h1>
          <p className="report-copy mx-auto mt-4 max-w-2xl text-center text-lg leading-8 text-[#4d607a] print:mt-3 print:text-base print:leading-7">
            A premium numerology blueprint designed for clarity, alignment, and practical action.
          </p>
          <div className="report-copy mt-3 text-center text-[11px] leading-5 text-[#6f6253] sm:text-xs print:mt-2">
            <p className="mt-1 text-[13px] font-semibold text-[#173a63]">Inspired by the teachings of</p>
            <p className="text-[14px] font-bold text-[#173a63]">Acharya Ravi Shankar</p>
            <a
              href="https://www.youtube.com/@LifeSignify"
              target="_blank"
              rel="noreferrer"
              className="mt-0.5 inline-block text-[12px] font-semibold text-[#1f4a7a] underline underline-offset-2"
            >
              YouTube: https://www.youtube.com/@LifeSignify
            </a>
            <p>Founder - LifeSignify</p>
            <p className="mt-1 font-semibold text-[#173a63]">Archana Shankar, Numerology Research &amp; Practice Head</p>
            <p>Managing Director &amp; CEO - LifeSignify</p>
          </div>
          {llmOnly ? null : (
            <div className="mt-5 grid gap-4 print:mt-3 print:grid-cols-2 print:gap-3 sm:grid-cols-2">
            <InfoCard
              title="Personal Profile (व्यक्तिगत प्रोफाइल)"
              tone="soft"
              lines={[
                `नाम: ${input.name || "Not Provided"}`,
                `जन्म तिथि: ${formatDate(input.date_of_birth)}`,
                `वर्तमान शहर: ${input.birth_place || "Not Provided"}`,
                `जेंडर: ${humanizeEnum(input.gender)}`,
              ]}
            />
            <InfoCard
              title="Current Focus (वर्तमान फोकस)"
              tone="accent"
              lines={[
                `ईमेल: ${input.email || "Not Provided"}`,
                `मोबाइल: ${input.mobile || "Not Provided"}`,
                `प्राथमिक चुनौती: ${humanizeEnum(input.current_problem || "general_alignment")}`,
                `Generated On: ${formatDate(report.content?.meta?.generated_at || report.created_at)}`,
              ]}
            />
          </div>
          )}
        </div>

        {llmOnly ? null : (
          <div className="grid w-full grid-cols-2 gap-3 print:grid-cols-4 lg:col-span-2 lg:grid-cols-4">
            <MetricPill
              label="Life Stability"
              value={metrics?.life_stability_index ?? "--"}
              valueClass={numberClass(metrics?.life_stability_index)}
              size="cover"
            />
            <MetricPill
              label="Confidence"
              value={metrics?.confidence_score ?? "--"}
              valueClass={numberClass(metrics?.confidence_score)}
              size="cover"
            />
            <MetricPill label="Risk Band" value={metrics?.risk_band ?? "--"} size="cover" />
            <MetricPill label="Personal Year" value={numbers?.personal_year ?? "--"} size="cover" />
          </div>
        )}
      </div>

      {llmOnly ? null : (
        <div className="report-cover-summary mt-6 grid gap-3 print:mt-4 print:grid-cols-5 print:gap-2 sm:grid-cols-2 lg:grid-cols-5">
          <MetricPill label="Mulank" value={numbers?.mulank ?? "--"} size="cover" />
          <MetricPill label="Bhagyank" value={numbers?.bhagyank ?? "--"} size="cover" />
          <MetricPill label="Name Energy" value={numbers?.name_energy ?? "--"} size="cover" />
          <MetricPill label="Mobile Vibration" value={numbers?.mobile_total ?? "--"} size="cover" />
          <MetricPill label="Email Energy" value={numbers?.email_energy ?? "--"} size="cover" />
        </div>
      )}
      <div className="report-cover-footer report-copy mt-auto pt-1 text-center text-[11px] leading-5 text-[#6f6253] sm:text-xs print:pt-0">
        <p>Designing Intelligent AI Systems: Research &amp; Architecture</p>
        <p className="font-semibold text-[#173a63]">Preeti Jay Vishvakarma - M.Tech, IIT Jodhpur</p>
      </div>
      </div>
    </ReportPage>
  );
}

function SectionContent({ section, report }: { section: HindiSection; report: ReportResponse }) {
  const lines = (section.blocks || []).filter((item) => String(item || "").trim());
  const layout = String(section.layout || "").toLowerCase();
  const normalizedSectionKey = SECTION_KEY_ALIAS_MAP[section.key] || section.key;
  const normalizedSectionTitle = repairDisplayText(section.title || "").toLowerCase();
  const isLifeIntelligencePage = normalizedSectionKey === "dashboard";
  const isProfileIntelligencePage = normalizedSectionKey === "profile";
  const isStrategicOverviewPage = normalizedSectionKey === "executive_summary";
  const isNumberDynamicsPage =
    normalizedSectionKey === "number_interaction" ||
    normalizedSectionKey === "number_dynamics" ||
    normalizedSectionTitle.includes("number dynamics") ||
    normalizedSectionTitle.includes("????????");
  const isCurrentFocusInsightsPage =
    normalizedSectionKey === "focus_snapshot" ||
    normalizedSectionTitle.includes("current focus insights") ||
    normalizedSectionTitle.includes("????");
  const isYearlyGuidancePage =
    normalizedSectionKey === "personal_year" ||
    normalizedSectionKey === "personal_year_direction" ||
    normalizedSectionKey === "yearly_guidance" ||
    normalizedSectionTitle.includes("personal year") ||
    normalizedSectionTitle.includes("yearly guidance") ||
    normalizedSectionTitle.includes("???????") ||
    normalizedSectionTitle.includes("????");
  const isFavorableTimingPage =
    normalizedSectionKey === "lucky_dates" ||
    normalizedSectionTitle.includes("favorable timing") ||
    normalizedSectionTitle.includes("?????? ???");
  const isEnergyAlignmentPage =
    normalizedSectionKey === "color_alignment" ||
    normalizedSectionTitle.includes("energy alignment");
  const usesYearlyStyleTemplate = isYearlyGuidancePage || isFavorableTimingPage;
  const isPersonalityIntelligencePage =
    normalizedSectionKey === "personality_profile" ||
    normalizedSectionTitle.includes("personality intelligence") ||
    normalizedSectionTitle.includes("??????????");
  const isActionRemediesPage =
    normalizedSectionKey === "remedy" ||
    normalizedSectionTitle.includes("action remedies");
  const isFinalInsightsPage =
    normalizedSectionKey === "closing_summary" ||
    normalizedSectionTitle.includes("final insights");
  const isCoreNumerologyPage = normalizedSectionKey === "core_numbers";
  const isBasicSection = normalizedSectionKey.startsWith("basic_");
  const deterministic = report.content?.deterministic;
  const numbers = getResolvedNumbers(report);
  const compatibility = deterministic?.mobile_life_compatibility;
  const loShu = deterministic?.lo_shu;
  const colorAlignment = deterministic?.color_alignment;
  const luckyNumbers = deterministic?.lucky_numbers;
  const remedy = deterministic?.remedy;
  const personalYear = deterministic?.personal_year;
  const closing = deterministic?.closing;

  if (isBasicSection) {
    return null;
  }

  const renderYearlyOrFavorableTemplate = (parsed: Array<{ key: string; label: string; value: string }>) => {
    const takeBy = (predicate: (label: string) => boolean) => parsed.find((entry) => predicate(entry.label.toLowerCase()));
    const coreInsight = takeBy((label) => label.includes("your core insight") || label.includes("????? ???????????"));
    const naturalStrength = takeBy((label) => label.includes("your natural strength") || label.includes("????????? ?????"));
    const growthEdge = takeBy((label) => label.includes("your growth edge") || label.includes("????? ???????"));
    const actionPath = takeBy((label) => label.includes("your action path") || label.includes("????? ?????"));
    const keyTraits = takeBy((label) => label.includes("your key traits") || label.includes("?????? ???"));

    const reserved = new Set([coreInsight, naturalStrength, growthEdge, actionPath, keyTraits].filter(Boolean).map((item) => item!.key));
    const extraCards = parsed.filter((item) => !reserved.has(item.key));

    if (isFavorableTimingPage) {
      const luckyNodeSource = Array.isArray((luckyNumbers as Record<string, any> | undefined)?.numbers)
        ? (((luckyNumbers as Record<string, any>).numbers as Array<string | number>).map((n) => String(n)))
        : [];
      const luckyFromText =
        String(coreInsight?.value || keyTraits?.value || "")
          .match(/\d+/g)
          ?.slice(0, 3) || [];
      const highlightedNodes = (luckyNodeSource.length ? luckyNodeSource : luckyFromText).slice(0, 3);

      return (
        <div className="fav-timing-flow">
          <div className="fav-timing-top">
            <FavorableTimingVisual highlightedNodes={highlightedNodes.length ? highlightedNodes : ["1", "4", "6"]} />

            <div className="fav-timing-cards fav-timing-cards--stack">
              {coreInsight ? (
                <InfoCard key={coreInsight.key} title={coreInsight.label} tone="accent" className="fav-timing-card" lines={[coreInsight.value]} />
              ) : null}
              {naturalStrength ? (
                <InfoCard key={naturalStrength.key} title={naturalStrength.label} tone="soft" className="fav-timing-card" lines={[naturalStrength.value]} />
              ) : null}
              {growthEdge ? (
                <InfoCard key={growthEdge.key} title={growthEdge.label} tone="soft" className="fav-timing-card" lines={[growthEdge.value]} />
              ) : null}
              {actionPath ? (
                <InfoCard
                  key={actionPath.key}
                  title={actionPath.label}
                  tone="default"
                  className="fav-timing-card report-profile-action life-intel-action"
                  lines={[actionPath.value]}
                />
              ) : null}
            </div>
          </div>

          {keyTraits ? (
            <InfoCard
              key={keyTraits.key}
              title={keyTraits.label}
              tone="soft"
              className={cx("fav-timing-traits", !extraCards.length && "fav-timing-traits--stretch")}
              lines={[keyTraits.value]}
            />
          ) : null}

          {extraCards.length ? (
            <div className="fav-timing-tail grid gap-3 md:grid-cols-2">
              {extraCards.map((item) => (
                <InfoCard key={`fav-extra-${item.key}`} title={item.label} tone="soft" lines={[item.value]} />
              ))}
            </div>
          ) : null}
        </div>
      );
    }

    return (
      <div className="yearly-guidance-flow">
        <div className="yearly-guidance-grid">
          {coreInsight ? (
            <InfoCard
              key={coreInsight.key}
              title={coreInsight.label}
              tone="accent"
              className="yearly-guidance-card"
              lines={[coreInsight.value]}
            />
          ) : null}
          {naturalStrength ? (
            <InfoCard
              key={naturalStrength.key}
              title={naturalStrength.label}
              tone="soft"
              className="yearly-guidance-card"
              lines={[naturalStrength.value]}
            />
          ) : null}
          {growthEdge ? (
            <InfoCard
              key={growthEdge.key}
              title={growthEdge.label}
              tone="soft"
              className="yearly-guidance-card"
              lines={[growthEdge.value]}
            />
          ) : null}
          {actionPath ? (
            <InfoCard
              key={actionPath.key}
              title={actionPath.label}
              tone="soft"
              className="yearly-guidance-card"
              lines={[actionPath.value]}
            />
          ) : null}
        </div>

        {keyTraits ? (
          <InfoCard
            key={keyTraits.key}
            title={keyTraits.label}
            tone="soft"
            className={cx("yearly-guidance-traits", !extraCards.length && "yearly-guidance-traits--stretch")}
            lines={[keyTraits.value]}
          />
        ) : null}

        {extraCards.length ? (
          <div className="yearly-guidance-tail grid gap-3 md:grid-cols-2">
            {extraCards.map((item) => (
              <InfoCard key={`yearly-extra-${item.key}`} title={item.label} tone="soft" lines={[item.value]} />
            ))}
          </div>
        ) : null}
      </div>
    );
  };

  const renderEnergyAlignmentTemplate = (parsed: Array<{ key: string; label: string; value: string }>) => {
    const takeBy = (predicate: (label: string) => boolean) => parsed.find((entry) => predicate(entry.label.toLowerCase()));
    const coreInsight = takeBy((label) => label.includes("your core insight") || label.includes("मुख्य अंतर्दृष्टि"));
    const naturalStrength = takeBy((label) => label.includes("your natural strength") || label.includes("स्वाभाविक शक्ति"));
    const growthEdge = takeBy((label) => label.includes("your growth edge") || label.includes("विकास क्षेत्र"));
    const actionPath = takeBy((label) => label.includes("your action path") || label.includes("कार्य मार्ग"));
    const keyTraits = takeBy((label) => label.includes("your key traits") || label.includes("प्रमुख गुण"));

    const reserved = new Set([coreInsight, naturalStrength, growthEdge, actionPath, keyTraits].filter(Boolean).map((item) => item!.key));
    const extraCards = parsed.filter((item) => !reserved.has(item.key));

    const rawColorList = Array.isArray((colorAlignment as Record<string, any> | undefined)?.favorable)
      ? (((colorAlignment as Record<string, any>).favorable as Array<unknown>).map((item) => repairDisplayText(String(item || ""))))
      : [];
    const fallbackPaletteText = [coreInsight?.value, keyTraits?.value, naturalStrength?.value, growthEdge?.value]
      .filter(Boolean)
      .join(" ");
    const palette = buildEnergyPalette(rawColorList, fallbackPaletteText);

    return (
      <div className="energy-align-flow">
        <div className="energy-align-top">
          <EnergyAlignmentVisual palette={palette} />

          <div className="energy-align-cards energy-align-cards--stack">
            {coreInsight ? (
              <InfoCard key={coreInsight.key} title={coreInsight.label} tone="accent" className="energy-align-card" lines={[coreInsight.value]} />
            ) : null}
            {naturalStrength ? (
              <InfoCard
                key={naturalStrength.key}
                title={naturalStrength.label}
                tone="soft"
                className="energy-align-card"
                lines={[naturalStrength.value]}
              />
            ) : null}
            {growthEdge ? (
              <InfoCard key={growthEdge.key} title={growthEdge.label} tone="soft" className="energy-align-card" lines={[growthEdge.value]} />
            ) : null}
            {actionPath ? (
              <InfoCard
                key={actionPath.key}
                title={actionPath.label}
                tone="default"
                className="energy-align-card report-profile-action life-intel-action"
                lines={[actionPath.value]}
              />
            ) : null}
          </div>
        </div>

        {keyTraits ? (
          <InfoCard
            key={keyTraits.key}
            title={keyTraits.label}
            tone="soft"
            className={cx("energy-align-traits", !extraCards.length && "energy-align-traits--stretch")}
            lines={[keyTraits.value]}
          />
        ) : null}

        {extraCards.length ? (
          <div className="energy-align-tail grid gap-3 md:grid-cols-2">
            {extraCards.map((item) => (
              <InfoCard key={`energy-extra-${item.key}`} title={item.label} tone="soft" lines={[item.value]} />
            ))}
          </div>
        ) : null}
      </div>
    );
  };

  const renderActionRemediesTemplate = (parsed: Array<{ key: string; label: string; value: string }>) => {
    const takeBy = (predicate: (label: string) => boolean) => parsed.find((entry) => predicate(entry.label.toLowerCase()));
    const coreInsight = takeBy((label) => label.includes("your core insight"));
    const naturalStrength = takeBy((label) => label.includes("your natural strength"));
    const growthEdge = takeBy((label) => label.includes("your growth edge"));
    const actionPath = takeBy((label) => label.includes("your action path"));
    const keyTraits = takeBy((label) => label.includes("your key traits"));

    const reserved = new Set([coreInsight, naturalStrength, growthEdge, actionPath, keyTraits].filter(Boolean).map((item) => item!.key));
    const extraCards = parsed.filter((item) => !reserved.has(item.key));

    const traitTokens = String(keyTraits?.value || "")
      .split(/[,|/]/)
      .map((item) => repairDisplayText(item).trim())
      .filter(Boolean);

    const fallbackTokens = [remedy?.anchor, remedy?.behaviour, remedy?.donation]
      .map((item) => repairDisplayText(String(item || "")).trim())
      .filter(Boolean);

    const protocolItems = Array.from(new Set([...traitTokens, ...fallbackTokens])).slice(0, 3);
    while (protocolItems.length < 3) {
      protocolItems.push(`Action Protocol ${protocolItems.length + 1}`);
    }

    const protocolHint = (item: string) => {
      const normalized = item.toLowerCase();
      if (normalized.includes("affirm") || normalized.includes("??????")) return "Daily positive affirmations";
      if (normalized.includes("time") || normalized.includes("???")) return "Time management techniques";
      if (normalized.includes("medit") || normalized.includes("?????") || normalized.includes("???")) return "Meditation and yoga";
      return item;
    };

    const protocolIcons = ["?", "?", "?"];

    return (
      <div className="remedy-premium-flow">
        <div className="remedy-premium-protocols">
          {protocolItems.map((item, index) => (
            <div key={`remedy-protocol-${index}`} className="remedy-premium-protocol">
              <div className="remedy-premium-protocol__icon" aria-hidden="true">
                {protocolIcons[index] || "?"}
              </div>
              <div className="remedy-premium-protocol__content">
                <p className="remedy-premium-protocol__en">{`Protocol ${index + 1}: ${protocolHint(item)}`}</p>
                <p className="remedy-premium-protocol__hi">{item}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="remedy-premium-summary">
          {coreInsight ? (
            <div className="remedy-premium-summary__title">
              {coreInsight.label}
            </div>
          ) : null}

          <div className="remedy-premium-summary__body">
            {coreInsight ? <p>{coreInsight.value}</p> : null}
            {naturalStrength ? (
              <p>
                <strong>{naturalStrength.label}: </strong>
                {naturalStrength.value}
              </p>
            ) : null}
            {growthEdge ? (
              <p>
                <strong>{growthEdge.label}: </strong>
                {growthEdge.value}
              </p>
            ) : null}
          </div>

          {actionPath ? (
            <div className="remedy-premium-summary__action">
              <p className="remedy-premium-summary__action-title">{actionPath.label}</p>
              <p className="remedy-premium-summary__action-copy">{actionPath.value}</p>
            </div>
          ) : null}
        </div>

        {keyTraits ? (
          <InfoCard
            key={keyTraits.key}
            title={keyTraits.label}
            tone="soft"
            className={cx("remedy-premium-traits", !extraCards.length && "remedy-premium-traits--stretch")}
            lines={[keyTraits.value]}
          />
        ) : null}

        {extraCards.length ? (
          <div className="remedy-premium-tail grid gap-3 md:grid-cols-2">
            {extraCards.map((item) => (
              <InfoCard key={`remedy-extra-${item.key}`} title={item.label} tone="soft" lines={[item.value]} />
            ))}
          </div>
        ) : null}
      </div>
    );
  };

  const renderFinalInsightsTemplate = (parsed: Array<{ key: string; label: string; value: string }>) => {
    const takeBy = (predicate: (label: string) => boolean) => parsed.find((entry) => predicate(entry.label.toLowerCase()));
    const coreInsight = takeBy((label) => label.includes("your core insight"));
    const naturalStrength = takeBy((label) => label.includes("your natural strength"));
    const growthEdge = takeBy((label) => label.includes("your growth edge"));
    const actionPath = takeBy((label) => label.includes("your action path"));
    const keyTraits = takeBy((label) => label.includes("your key traits"));

    const reserved = new Set([coreInsight, naturalStrength, growthEdge, actionPath, keyTraits].filter(Boolean).map((item) => item!.key));
    const extraCards = parsed.filter((item) => !reserved.has(item.key));

    const traitTokens = String(keyTraits?.value || "")
      .split(/[,|/]/)
      .map((item) => repairDisplayText(item).trim())
      .filter(Boolean);

    const fallbackTraits = ["Discipline", "Leadership", "Positivity"];
    const traits = [...traitTokens];
    for (const fallback of fallbackTraits) {
      if (traits.length >= 3) break;
      traits.push(fallback);
    }

    return (
      <div className="final-insights-flow">
        <div className="final-insights-stage rounded-[24px] border border-[#c8aa66] p-4">
          <img src={ASSETS.mandala} alt="" aria-hidden="true" loading="lazy" decoding="async" className="final-insights-stage__bg" />
          <div className="final-insights-stage__halo" aria-hidden="true" />

          <div className="final-insights-stage__center" aria-hidden="true">
            <p className="final-insights-stage__center-text">Execution</p>
          </div>

          <div className="final-insights-stage__trait final-insights-stage__trait--top">
            {traits[0]}
          </div>
          <div className="final-insights-stage__trait final-insights-stage__trait--left">
            {traits[1]}
          </div>
          <div className="final-insights-stage__trait final-insights-stage__trait--right">
            {traits[2]}
          </div>

          <div className="final-insights-stage__note final-insights-stage__note--summary">
            {coreInsight ? <p>{coreInsight.value}</p> : null}
            {naturalStrength ? <p>{naturalStrength.value}</p> : null}
          </div>

          {growthEdge ? (
            <div className="final-insights-stage__note final-insights-stage__note--growth">
              <p className="final-insights-stage__note-title">{growthEdge.label}</p>
              <p>{growthEdge.value}</p>
            </div>
          ) : null}

          {actionPath ? (
            <div className="final-insights-stage__note final-insights-stage__note--action">
              <p className="final-insights-stage__note-title">{actionPath.label}</p>
              <p>{actionPath.value}</p>
            </div>
          ) : null}
        </div>

        {keyTraits ? (
          <InfoCard
            key={keyTraits.key}
            title={keyTraits.label}
            tone="soft"
            className={cx("final-insights-traits", !extraCards.length && "final-insights-traits--stretch")}
            lines={[keyTraits.value]}
          />
        ) : null}

        {extraCards.length ? (
          <div className="final-insights-tail grid gap-3 md:grid-cols-2">
            {extraCards.map((item) => (
              <InfoCard key={`final-extra-${item.key}`} title={item.label} tone="soft" lines={[item.value]} />
            ))}
          </div>
        ) : null}
      </div>
    );
  };

  if (usesYearlyStyleTemplate && layout !== "premium_card") {
    const parsed = lines
      .map((line, idx) => {
        const item = parseLine(line);
        return {
          key: `${section.key}-yearly-${idx}`,
          label: repairDisplayText(item.label || `Key Point ${idx + 1}`),
          value: repairDisplayText(item.value || line),
        };
      })
      .filter((entry) => String(entry.value || "").trim());

    return renderYearlyOrFavorableTemplate(parsed);
  }

  if (isEnergyAlignmentPage && layout !== "premium_card") {
    const parsed = lines
      .map((line, idx) => {
        const item = parseLine(line);
        return {
          key: `${section.key}-energy-${idx}`,
          label: repairDisplayText(item.label || `Key Point ${idx + 1}`),
          value: repairDisplayText(item.value || line),
        };
      })
      .filter((entry) => String(entry.value || "").trim());

    return renderEnergyAlignmentTemplate(parsed);
  }

  if (isActionRemediesPage && layout !== "premium_card") {
    const parsed = lines
      .map((line, idx) => {
        const item = parseLine(line);
        return {
          key: `${section.key}-remedy-${idx}`,
          label: repairDisplayText(item.label || `Key Point ${idx + 1}`),
          value: repairDisplayText(item.value || line),
        };
      })
      .filter((entry) => String(entry.value || "").trim());

    return renderActionRemediesTemplate(parsed);
  }

  if (isFinalInsightsPage && layout !== "premium_card") {
    const parsed = lines
      .map((line, idx) => {
        const item = parseLine(line);
        return {
          key: `${section.key}-final-${idx}`,
          label: repairDisplayText(item.label || `Key Point ${idx + 1}`),
          value: repairDisplayText(item.value || line),
        };
      })
      .filter((entry) => String(entry.value || "").trim());

    return renderFinalInsightsTemplate(parsed);
  }

  if (layout === "hero_summary") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
          <InfoCard
            title="??????? ???"
            tone="accent"
            lines={lines.slice(0, 1)}
            className="h-full"
            imageSrc={getNumberImage(numbers?.mulank)}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            {lines.slice(1, 5).map((line, idx) => {
              const item = parseLine(line);
              return (
                <InfoCard
                  key={`${section.key}-hero-${idx}`}
                  title={item.label || `????? ????? ${idx + 1}`}
                  tone="soft"
                  lines={[item.value || line]}
                  imageSrc={idx % 2 === 0 ? ASSETS.lotus : ASSETS.chakra}
                />
              );
            })}
          </div>
        </div>
        {lines.slice(5).length ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {lines.slice(5).map((line, idx) => (
              <HighlightStrip key={`${section.key}-strip-${idx}`} text={line} />
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  if (layout === "triad_cards") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-3">
          {lines.slice(0, 3).map((line, idx) => {
            const item = parseLine(line);
            return (
              <InfoCard
                key={`${section.key}-triad-${idx}`}
                title={item.label || `????? ????? ${idx + 1}`}
                tone={idx === 1 ? "accent" : "soft"}
                lines={[item.value || line]}
                className="h-full"
                imageSrc={getNumberImage([numbers?.mulank, numbers?.bhagyank, numbers?.name_energy][idx])}
              />
            );
          })}
        </div>
        {lines.length > 3 ? (
          <InfoCard title="???????? ?? ??????? ??????" lines={lines.slice(3)} imageSrc={ASSETS.chakra} />
        ) : null}
      </div>
    );
  }

  if (layout === "main_card_plus_strips") {
    const stripColumns = splitIntoColumns(lines.slice(2), 2);
    return (
      <div className="grid gap-4 lg:grid-cols-[1.02fr,0.98fr]">
        <InfoCard
          title="????? ????????"
          tone="accent"
          lines={lines.slice(0, 2)}
          className="h-full"
          imageSrc={getNumberImage(numbers?.mulank)}
        />
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-1">
          {stripColumns.map((group, groupIndex) => (
            <div key={`${section.key}-main-group-${groupIndex}`} className="space-y-3">
              {group.map((line, idx) => (
                <HighlightStrip key={`${section.key}-main-${groupIndex}-${idx}`} text={line} />
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (layout === "split_insight") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <InfoCard title="???? ?????" tone="soft" lines={lines.slice(0, 2)} className="h-full" imageSrc={ASSETS.lotus} />
          <InfoCard
            title="??????? ????????????"
            tone="accent"
            lines={lines.slice(2, 4).length ? lines.slice(2, 4) : lines.slice(0, 2)}
            className="h-full"
            imageSrc={getNumberImage(numbers?.bhagyank)}
          />
        </div>
        {lines[4] ? <HighlightStrip text={lines[4]} /> : null}
      </div>
    );
  }

  if (layout === "center_feature") {
    const featureGroups = splitIntoColumns(lines.slice(2), 2);
    return (
      <div className="grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
        <InfoCard
          title="?????? ???"
          tone="accent"
          lines={lines.slice(0, 2)}
          className="h-full"
          imageSrc={getNumberImage(numbers?.name_energy)}
        />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
          {featureGroups.map((group, groupIndex) => (
            <div key={`${section.key}-feature-group-${groupIndex}`} className="grid gap-4">
              {group.map((line, idx) => {
                const item = parseLine(line);
                return (
                  <InfoCard
                    key={`${section.key}-feature-${groupIndex}-${idx}`}
                title={item.label || `????? ????? ${groupIndex * 2 + idx + 1}`}
                tone="soft"
                lines={[item.value || line]}
                imageSrc={(groupIndex + idx) % 2 === 0 ? ASSETS.chakra : ASSETS.lotus}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (layout === "triad_interaction") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-3">
          {lines.slice(0, 3).map((line, idx) => {
            const item = parseLine(line);
            return (
              <InfoCard
                key={`${section.key}-interaction-${idx}`}
                title={item.label || `??? ${idx + 1}`}
                tone={idx === 1 ? "accent" : "soft"}
                lines={[item.value || line]}
                imageSrc={idx === 0 ? getNumberImage(numbers?.mulank) : idx === 1 ? getNumberImage(numbers?.bhagyank) : getNumberImage(numbers?.name_energy)}
              />
            );
          })}
        </div>
        {lines.length > 3 ? <InfoCard title="????? ????????" lines={lines.slice(3)} imageSrc={ASSETS.chakra} /> : null}
      </div>
    );
  }

  if (layout === "diagnostic_grid") {
    const loShuTitle =
      languageMode === "english"
        ? "Lo Shu Analysis"
        : languageMode === "bilingual"
          ? "लो शू विश्लेषण | Lo Shu Analysis"
          : languageMode === "hinglish"
            ? "Lo Shu Vishleshan"
            : "लो शू विश्लेषण";
    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-[0.95fr,1.05fr]">
          <LoShuGridCard loShu={loShu} languageMode={languageMode} />
          <InfoCard title={loShuTitle} tone="soft" lines={lines.slice(0, 4)} className="h-full" imageSrc={ASSETS.mandala} />
        </div>
        {lines[4] ? <HighlightStrip text={lines[4]} /> : null}
      </div>
    );
  }

  if (layout === "diagnostic_tiles") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {lines.slice(0, 6).map((line, idx) => {
            const item = parseLine(line);
            return (
              <InfoCard
                key={`${section.key}-tile-${idx}`}
                title={item.label || `?? ${idx + 1}`}
                tone="soft"
                lines={[item.value || line]}
                imageSrc={getNumberImage(Number(item.label?.match(/\d+/)?.[0] || idx + 1))}
              />
            );
          })}
        </div>
        {lines.slice(6).length ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {lines.slice(6).map((line, idx) => (
              <HighlightStrip key={`${section.key}-tile-strip-${idx}`} text={line} />
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  if (layout === "spotlight_chips") {
    return (
      <div className="space-y-4">
        <div className="grid gap-5 lg:grid-cols-[0.78fr,1.22fr]">
          <div className="space-y-3">
            {lines.slice(0, 3).map((line, idx) => {
              const item = parseLine(line);
              return (
                <InfoCard
                  key={`${section.key}-chip-${idx}`}
                  title={item.label || `Energy ${idx + 1}`}
                  tone="accent"
                  lines={[item.value || line]}
                  imageSrc={getNumberImage(numbers?.mulank)}
                />
              );
            })}
          </div>
          <InfoCard title="?????? ???????" tone="soft" lines={lines.slice(3)} className="h-full" imageSrc={ASSETS.chakra} />
        </div>
      </div>
    );
  }

  if (layout === "calculation_split") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <InfoCard title="???? ????" tone="accent" lines={lines.slice(0, 2)} className="h-full" imageSrc={ASSETS.chakra} />
          <InfoCard
            title="?????? ????????"
            tone="soft"
            lines={lines.slice(2, 5).length ? lines.slice(2, 5) : lines.slice(0, 2)}
            className="h-full"
            imageSrc={getNumberImage(numbers?.mobile_total)}
          />
        </div>
        {lines[5] ? <HighlightStrip text={lines[5]} /> : null}
      </div>
    );
  }

  if (layout === "comparison_meter") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 xl:grid-cols-[1fr,1fr,0.82fr]">
          <InfoCard title="???? ?? ?????" tone="soft" lines={lines.slice(0, 2)} imageSrc={getNumberImage(numbers?.bhagyank)} />
          <InfoCard
            title="?????? ?????? ?????"
            tone="soft"
            lines={lines.slice(2, 4).length ? lines.slice(2, 4) : lines.slice(0, 2)}
            imageSrc={getNumberImage(numbers?.mobile_total)}
          />
          <CompatibilityMeter compatibility={compatibility} />
        </div>
        {lines[4] ? <HighlightStrip text={lines[4]} /> : null}
      </div>
    );
  }

  if (layout === "four_card_grid") {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {lines.map((line, idx) => {
          const item = parseLine(line);
          return (
            <InfoCard
              key={`${section.key}-grid-${idx}`}
              title={item.label || `Profile ${idx + 1}`}
              tone={idx % 2 === 0 ? "soft" : "default"}
              lines={[item.value || line]}
              className="h-full"
              imageSrc={idx % 2 === 0 ? ASSETS.lotus : ASSETS.chakra}
            />
          );
        })}
      </div>
    );
  }

  if (layout === "timeline_strategy") {
    const stageGroups = splitIntoColumns(lines.slice(2), 2);
    return (
      <div className="grid gap-4 lg:grid-cols-[0.9fr,1.1fr]">
        <InfoCard title="??????? ???" tone="accent" lines={lines.slice(0, 2)} imageSrc={getCoverVisual(report)} />
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-1">
          {stageGroups.map((group, groupIndex) => (
            <div key={`${section.key}-timeline-group-${groupIndex}`} className="space-y-3">
              {group.map((line, idx) => (
                <HighlightStrip
                  key={`${section.key}-timeline-${groupIndex}-${idx}`}
                  text={`??? ${groupIndex * 2 + idx + 1}: ${line.replace(/\*\*/g, "")}`}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (layout === "split_analysis") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <InfoCard title="????? ????" tone="soft" lines={lines.slice(0, 2)} className="h-full" imageSrc={getNumberImage(numbers?.bhagyank)} />
          <InfoCard
            title="?? ???????"
            tone="soft"
            lines={lines.slice(2, 4).length ? lines.slice(2, 4) : lines.slice(0, 2)}
            className="h-full"
            imageSrc={getNumberImage(numbers?.mobile_total)}
          />
        </div>
        {lines[4] ? <HighlightStrip text={lines[4]} /> : null}
      </div>
    );
  }

  if (layout === "dual_card_warning") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <InfoCard title="????????? ????" tone="soft" lines={lines.slice(0, 1)} imageSrc={getNumberImage(numbers?.mulank)} />
          <InfoCard title="????? ?????????" tone="soft" lines={lines.slice(1, 2).length ? lines.slice(1, 2) : lines.slice(0, 1)} imageSrc={ASSETS.lotus} />
        </div>
        <div className="grid gap-4 lg:grid-cols-[1fr,0.95fr]">
          {lines[2] ? <HighlightStrip text={lines[2]} /> : null}
          {lines[3] ? <InfoCard title="????????? ?? ???" tone="accent" lines={[lines[3]]} imageSrc={ASSETS.om} /> : null}
        </div>
      </div>
    );
  }

  if (layout === "wellness_diagnostics") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-3">
          {lines.slice(0, 3).map((line, idx) => {
            const item = parseLine(line);
            return (
              <InfoCard
                key={`${section.key}-wellness-${idx}`}
                title={item.label || `????????? ????? ${idx + 1}`}
                tone={idx === 1 ? "accent" : "soft"}
                lines={[item.value || line]}
                imageSrc={idx === 0 ? ASSETS.chakra : idx === 1 ? ASSETS.lotus : ASSETS.om}
              />
            );
          })}
        </div>
        {lines[3] ? <HighlightStrip text={lines[3]} /> : null}
      </div>
    );
  }

  if (layout === "forecast_badge") {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 xl:grid-cols-[0.72fr,1.28fr]">
          <InfoCard
            title="???? ?????"
            tone="accent"
            lines={[lines[0] || `Personal Year: ${numbers?.personal_year ?? "--"}`]}
            imageSrc={getNumberImage(numbers?.personal_year)}
          />
          <InfoCard
            title="???? ????????????"
            tone="soft"
            lines={[
              lines[1] || `Theme: ${personalYear?.theme || "N/A"}`,
              lines[2] || `Opportunities: ${personalYear?.opportunities || "N/A"}`,
              lines[3] || `Caution: ${personalYear?.caution || "N/A"}`,
            ]}
          />
        </div>
        <HighlightStrip
          text={lines[4] || `Action Direction: ${personalYear?.action_direction || " clear weekly goals ?? weekly tracking"}`}
        />
      </div>
    );
  }

  if (layout === "elegant_tiles") {
    const primary = luckyNumbers?.primary || [];
    const support = luckyNumbers?.support || [];
    const dates = luckyNumbers?.favorable_dates || [];

    return (
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-3">
          <ValueTiles title="?????? ??? ???" tone="accent" values={primary} imageSrc={getNumberImage(primary[0])} />
          <ValueTiles title="????? ???" tone="soft" values={support} imageSrc={getNumberImage(support[0])} />
          <ValueTiles title="?????? ???????" tone="soft" values={dates} imageSrc={ASSETS.chakra} />
        </div>
        {lines[3] ? <HighlightStrip text={lines[3]} /> : null}
      </div>
    );
  }

  if (layout === "palette_guide") {
    return (
      <div className="space-y-4">
        <ColorSwatches colors={colorAlignment?.favorable || []} />
        <div className="grid gap-4 md:grid-cols-2">
          {lines.map((line, idx) => {
            const item = parseLine(line);
            return (
              <InfoCard
                key={`${section.key}-palette-${idx}`}
                title={item.label || `??? ?????????? ${idx + 1}`}
                tone={idx === 0 ? "accent" : "soft"}
                lines={[item.value || line]}
                imageSrc={idx === 0 ? ASSETS.lotus : ASSETS.chakra}
              />
            );
          })}
        </div>
      </div>
    );
  }

  if (layout === "remedy_cards") {
    const remedyImage = getRemedyImage(remedy);

    return (
      <div className="space-y-4">
        <div className="grid gap-5 lg:grid-cols-[1.15fr,0.85fr]">
          <div className="grid gap-4 md:grid-cols-3">
            <InfoCard
              title="?????????? ????"
              tone="accent"
              lines={[lines[0] || `???: ${remedy?.anchor || "N/A"}`]}
              imageSrc={remedyImage}
            />
            <InfoCard
              title="????? ?????"
              tone="soft"
              lines={[lines[1] || `?????: ${remedy?.mantra || "N/A"}`, `??????: ${remedy?.repetition || "N/A"}`]}
              imageSrc={ASSETS.om}
            />
            <InfoCard
              title="??? ?? ????"
              tone="soft"
              lines={[lines[2] || `???: ${remedy?.donation || "N/A"}`, `????: ${remedy?.behaviour || "N/A"}`]}
            />
          </div>
          <div className="rounded-[24px] border border-[#cfb47c] bg-white/85 p-5 text-center">
            <img src={remedyImage} alt="Remedy deity" loading="lazy" decoding="async" className="mx-auto h-40 w-40 object-contain" />
            <p className="mt-4 text-sm font-semibold text-[#9c7941]">???? ??????</p>
            <p className="report-copy mt-2 text-base leading-7 text-[#214266]">{remedy?.anchor || "????? ??????"}</p>
          </div>
        </div>
        {lines[3] ? <HighlightStrip text={lines[3]} /> : null}
      </div>
    );
  }

  if (layout === "closing_reflection") {
    const parsed = lines
      .map((line, idx) => {
        const item = parseLine(line);
        return {
          key: `${section.key}-closing-${idx}`,
          label: repairDisplayText(item.label || `Key Point ${idx + 1}`),
          value: repairDisplayText(item.value || line),
        };
      })
      .filter((entry) => String(entry.value || "").trim());
    return renderFinalInsightsTemplate(parsed);
  }

  if (false && layout === "closing_reflection") {
    return (
      <div className="space-y-4">
        <InfoCard
            title="????? ?????"
            tone="accent"
            lines={[
            lines[0] || `????? ???? ???: ${closing?.life_theme || "N/A"}`,
            lines[1] || `????? ??????: ${closing?.key_challenge || "N/A"}`,
            lines[2] || `???????? ?????: ${(report.content?.deterministic?.priority_flags || []).join(", ") || "N/A"}`,
            lines[3] || `????? ??????????: ${closing?.final_guidance || "N/A"}`,
          ]}
          className="mx-auto max-w-4xl"
          imageSrc={ASSETS.om}
        />
        {lines[4] ? <HighlightStrip text={lines[4]} /> : null}
      </div>
    );
  }

  return (
    (() => {
      const parsed = lines.map((line, idx) => {
        const item = parseLine(line);
        return {
          key: `${section.key}-fallback-${idx}`,
          label: repairDisplayText(item.label || `????? ????? ${idx + 1}`),
          value: repairDisplayText(item.value || line),
        };
      });

      const withMatrix = (content: ReactNode) => {
        if (!isCoreNumerologyPage) return content;
        return content;
      };

      const takeBy = (predicate: (label: string) => boolean) => {
        const hit = parsed.find((entry) => predicate(entry.label.toLowerCase()));
        return hit;
      };

      const coreInsight = takeBy((label) => label.includes("your core insight") || label.includes("????? ???????????"));
      const naturalStrength = takeBy((label) => label.includes("your natural strength") || label.includes("????????? ?????"));
      const growthEdge = takeBy((label) => label.includes("your growth edge") || label.includes("????? ???????"));
      const actionPath = takeBy((label) => label.includes("your action path") || label.includes("????? ?????"));
      const keyTraits = takeBy((label) => label.includes("your key traits") || label.includes("?????? ???"));

      const lifePathMetric = takeBy((label) => label.includes("???? ??") || label.includes("life path"));
      const destinyMetric = takeBy((label) => label.includes("????? ??????") || label.includes("destiny"));
      const nameMetric = takeBy((label) => label.includes("??? ??????") || label.includes("name number"));
      const expressionMetric = takeBy((label) => label.includes("??????????") || label.includes("expression"));

      if (isProfileIntelligencePage) {
        const usedKeys = new Set(
          [
            coreInsight,
            naturalStrength,
            growthEdge,
            actionPath,
            keyTraits,
            lifePathMetric,
            destinyMetric,
            nameMetric,
          ]
            .filter(Boolean)
            .map((item) => item!.key),
        );

        const extraCards = parsed.filter((item) => !usedKeys.has(item.key));
        const metricCards = [lifePathMetric, destinyMetric, nameMetric].filter(Boolean) as Array<{
          key: string;
          label: string;
          value: string;
        }>;

        return withMatrix(
          <div className="report-profile-intel space-y-4">
            <div className="report-profile-topgrid grid items-start gap-4 lg:grid-cols-[0.88fr,1.12fr]">
              <ProfilePentagonSummary report={report} keyTraits={keyTraits?.value} />

              <div className="report-profile-story space-y-3">
                {coreInsight ? (
                  <InfoCard
                    key={coreInsight.key}
                    title={coreInsight.label}
                    tone="soft"
                    className="report-profile-core"
                    lines={[coreInsight.value]}
                  />
                ) : null}
                {naturalStrength ? <InfoCard key={naturalStrength.key} title={naturalStrength.label} tone="soft" lines={[naturalStrength.value]} /> : null}
                {growthEdge ? <InfoCard key={growthEdge.key} title={growthEdge.label} tone="soft" lines={[growthEdge.value]} /> : null}
              </div>
            </div>

            {actionPath ? (
              <InfoCard
                key={actionPath.key}
                title="Your Action Path (???? ????? ?????)"
                tone="default"
                className="report-profile-action report-profile-action-wide"
                lines={[actionPath.value]}
              />
            ) : null}

            {metricCards.length ? (
              <div className="report-profile-metrics grid gap-3 md:grid-cols-3">
                {metricCards.map((metric) => (
                  <InfoCard
                    key={metric.key}
                    title={metric.label}
                    tone="soft"
                    lines={[resolveMetricMeaning(metric.label, metric.value, report)]}
                  />
                ))}
              </div>
            ) : null}

            {extraCards.length ? (
              <div className="report-profile-extra grid gap-3 md:grid-cols-2">
                {extraCards.map((item) => (
                  <InfoCard key={item.key} title={item.label} tone="soft" lines={[item.value]} />
                ))}
              </div>
            ) : null}
          </div>
        );
      }

      if (isCoreNumerologyPage) {
        const metricCards = [lifePathMetric, destinyMetric, expressionMetric || nameMetric].filter(Boolean) as Array<{
          key: string;
          label: string;
          value: string;
        }>;
        const reserved = new Set(
          [coreInsight, naturalStrength, growthEdge, actionPath, keyTraits, ...metricCards]
            .filter(Boolean)
            .map((item) => item!.key),
        );
        const extraCards = parsed.filter((item) => !reserved.has(item.key));

        return (
          <div className="core-numai-flow core-numai-flow--waterfall">
            <CoreNumerologyPillarsVisual report={report} />

            <div className="core-numai-cards core-numai-cards--waterfall space-y-3">
              {coreInsight ? (
                <InfoCard
                  key={coreInsight.key}
                  title={coreInsight.label}
                  tone="accent"
                  className="core-numai-card core-numai-card--core life-intel-core"
                  lines={[coreInsight.value]}
                />
              ) : null}
              {naturalStrength ? (
                <InfoCard
                  key={naturalStrength.key}
                  title={naturalStrength.label}
                  tone="soft"
                  className="core-numai-card core-numai-card--strength"
                  lines={[naturalStrength.value]}
                />
              ) : null}
              {growthEdge ? (
                <InfoCard
                  key={growthEdge.key}
                  title={growthEdge.label}
                  tone="soft"
                  className="core-numai-card core-numai-card--edge"
                  lines={[growthEdge.value]}
                />
              ) : null}
              {actionPath ? (
                <InfoCard
                  key={actionPath.key}
                  title={actionPath.label}
                  tone="default"
                  className="core-numai-card core-numai-card--action report-profile-action life-intel-action"
                  lines={[actionPath.value]}
                />
              ) : null}
            </div>

            {keyTraits ? (
              <InfoCard
                key={keyTraits.key}
                title={keyTraits.label}
                tone="soft"
                className={cx("core-numai-traits", !metricCards.length && !extraCards.length && "core-numai-traits--stretch")}
                lines={[keyTraits.value]}
              />
            ) : null}

            {metricCards.length ? (
              <div className="core-numai-metrics-seq space-y-3">
                {metricCards.map((metric) => (
                  <InfoCard
                    key={`core-metric-${metric.key}`}
                    title={metric.label}
                    tone="soft"
                    className="core-numai-metric-card"
                    lines={[resolveMetricMeaning(metric.label, metric.value, report)]}
                  />
                ))}
              </div>
            ) : null}

            {extraCards.length ? (
              <div className="core-numai-extra-seq space-y-3">
                {extraCards.map((item) => (
                  <InfoCard key={`core-extra-${item.key}`} title={item.label} tone="soft" className="core-numai-extra-card" lines={[item.value]} />
                ))}
              </div>
            ) : null}
          </div>
        );
      }

      if (isNumberDynamicsPage) {
        const comboCard = parsed.find((item) => /combo|combination|interaction|synergy/i.test(item.label));
        const missingCard = parsed.find((item) => /missing|gap|weak|weakness/i.test(item.label));
        const reserved = new Set(
          [coreInsight, naturalStrength, growthEdge, actionPath, keyTraits, comboCard, missingCard]
            .filter(Boolean)
            .map((item) => item!.key),
        );
        const extraCards = parsed.filter((item) => !reserved.has(item.key));

        const deterministic = (report.content?.deterministic || {}) as Record<string, any>;
        const pyth = (deterministic.numerologyValues?.pythagorean || {}) as Record<string, any>;
        const chaldean = (deterministic.numerologyValues?.chaldean || {}) as Record<string, any>;
        const loshu = (deterministic.numerologyValues?.loshu_grid || {}) as Record<string, any>;

        const comboFromText = String(comboCard?.value || "")
          .match(/\d+/g)
          ?.slice(0, 3) || [];
        const fallbackCombo = [
          toNumber(pyth.life_path_number),
          toNumber(pyth.destiny_number),
          toNumber(chaldean.name_number),
        ]
          .filter((v) => v !== undefined)
          .slice(0, 3) as number[];
        const comboNumbers = (comboFromText.length ? comboFromText : fallbackCombo).map((x) => String(x));

        const missingFromDeterministic = Array.isArray(loshu.missing_numbers)
          ? (loshu.missing_numbers as Array<string | number>).map((x) => String(x))
          : [];
        const missingFromText =
          String(missingCard?.value || growthEdge?.value || "")
            .match(/\d+/g)
            ?.slice(0, 6) || [];
        const missingNumbers = (missingFromDeterministic.length ? missingFromDeterministic : missingFromText).slice(0, 6);

        return (
          <div className="number-dyn-flow number-dyn-flow--stack">
            <NumberDynamicsVisual
              report={report}
              comboNumbers={comboNumbers.length ? comboNumbers : ["4", "1", "3"]}
              missingNumbers={missingNumbers.length ? missingNumbers : ["2", "3", "5", "7", "8"]}
            />

            {coreInsight ? (
              <InfoCard
                key={coreInsight.key}
                title={coreInsight.label}
                tone="accent"
                className="number-dyn-card"
                lines={[coreInsight.value]}
              />
            ) : null}
            {naturalStrength ? (
              <InfoCard
                key={naturalStrength.key}
                title={naturalStrength.label}
                tone="soft"
                className="number-dyn-card"
                lines={[naturalStrength.value]}
              />
            ) : null}
            {growthEdge ? (
              <InfoCard
                key={growthEdge.key}
                title={growthEdge.label}
                tone="soft"
                className="number-dyn-card"
                lines={[growthEdge.value]}
              />
            ) : null}
            {actionPath ? (
              <InfoCard
                key={actionPath.key}
                title={actionPath.label}
                tone="default"
                className="number-dyn-card report-profile-action life-intel-action"
                lines={[actionPath.value]}
              />
            ) : null}
            {keyTraits ? (
              <InfoCard
                key={keyTraits.key}
                title={keyTraits.label}
                tone="soft"
                className="number-dyn-card number-dyn-keytraits"
                lines={[keyTraits.value]}
              />
            ) : null}

            {extraCards.length ? (
              <div className="number-dyn-tail">
                {extraCards.map((item) => (
                  <InfoCard key={`nd-extra-${item.key}`} title={item.label} tone="soft" lines={[item.value]} />
                ))}
              </div>
            ) : null}
          </div>
        );
      }

      if (isPersonalityIntelligencePage) {
        const strengthHighlight =
          parsed.find((item) => /strength|positive|trait/i.test(item.label)) ||
          naturalStrength;
        const riskHighlight =
          parsed.find((item) => /risk|challenge|negative/i.test(item.label)) ||
          growthEdge;

        const strengthText = repairDisplayText(strengthHighlight?.value || keyTraits?.value || "--");
        const riskText = repairDisplayText(riskHighlight?.value || "--");

        const reserved = new Set(
          [coreInsight, naturalStrength, growthEdge, actionPath, keyTraits, strengthHighlight, riskHighlight]
            .filter(Boolean)
            .map((item) => item!.key),
        );
        const extraCards = parsed.filter((item) => !reserved.has(item.key));

        return (
          <div className="personality-intel-flow">
            <div className="personality-intel-hero">
              <div className="personality-intel-hero__panel personality-intel-hero__panel--strength">
                <p className="personality-intel-hero__title">Strengths (????)</p>
                <p className="personality-intel-hero__value">{strengthText}</p>
              </div>
              <div className="personality-intel-hero__panel personality-intel-hero__panel--risk">
                <p className="personality-intel-hero__title">Risks (?????)</p>
                <p className="personality-intel-hero__value">{riskText}</p>
              </div>
            </div>

            {coreInsight ? (
              <InfoCard
                key={coreInsight.key}
                title={coreInsight.label}
                tone="accent"
                className="personality-intel-core"
                lines={[coreInsight.value]}
              />
            ) : null}

            {actionPath ? (
              <InfoCard
                key={actionPath.key}
                title={actionPath.label}
                tone="default"
                className="personality-intel-action report-profile-action life-intel-action"
                lines={[actionPath.value]}
              />
            ) : null}

            {keyTraits ? (
              <InfoCard
                key={keyTraits.key}
                title={keyTraits.label}
                tone="soft"
                className={cx("personality-intel-traits", !extraCards.length && "personality-intel-traits--stretch")}
                lines={[keyTraits.value]}
              />
            ) : null}

            {extraCards.length ? (
              <div className="personality-intel-tail grid gap-3 md:grid-cols-2">
                {extraCards.map((item) => (
                  <InfoCard key={`personality-extra-${item.key}`} title={item.label} tone="soft" lines={[item.value]} />
                ))}
              </div>
            ) : null}
          </div>
        );
      }

      if (isCurrentFocusInsightsPage) {
        const focusAreaCard =
          parsed.find((item) => /focus area|focus|current problem|alignment/i.test(item.label)) ||
          parsed.find((item) => /focus|alignment|problem/i.test(item.value));

        const focusText = repairDisplayText(
          focusAreaCard?.value ||
            String((report.content?.normalizedInput as Record<string, any> | undefined)?.focusArea || "General Alignment"),
        );

        const reserved = new Set(
          [coreInsight, naturalStrength, growthEdge, actionPath, keyTraits, focusAreaCard]
            .filter(Boolean)
            .map((item) => item!.key),
        );
        const extraCards = parsed.filter((item) => !reserved.has(item.key));

        return (
          <div className="focus-insights-flow">
            <div className="focus-insights-top">
              <FocusInsightsVisual focusText={focusText} />

              <div className="focus-insights-cards focus-insights-cards--stack">
                {coreInsight ? (
                  <InfoCard
                    key={coreInsight.key}
                    title={coreInsight.label}
                    tone="accent"
                    className="focus-insights-card"
                    lines={[coreInsight.value]}
                  />
                ) : null}
                {naturalStrength ? (
                  <InfoCard
                    key={naturalStrength.key}
                    title={naturalStrength.label}
                    tone="soft"
                    className="focus-insights-card"
                    lines={[naturalStrength.value]}
                  />
                ) : null}
                {growthEdge ? (
                  <InfoCard
                    key={growthEdge.key}
                    title={growthEdge.label}
                    tone="soft"
                    className="focus-insights-card"
                    lines={[growthEdge.value]}
                  />
                ) : null}
                {actionPath ? (
                  <InfoCard
                    key={actionPath.key}
                    title={actionPath.label}
                    tone="default"
                    className="focus-insights-card report-profile-action life-intel-action"
                    lines={[actionPath.value]}
                  />
                ) : null}
              </div>
            </div>

            {keyTraits ? (
              <InfoCard
                key={keyTraits.key}
                title={keyTraits.label}
                tone="soft"
                className={cx("focus-insights-traits", !extraCards.length && "focus-insights-traits--stretch")}
                lines={[keyTraits.value]}
              />
            ) : null}

            {extraCards.length ? (
              <div className="focus-insights-tail grid gap-3 md:grid-cols-2">
                {extraCards.map((item) => (
                  <InfoCard key={`focus-extra-${item.key}`} title={item.label} tone="soft" lines={[item.value]} />
                ))}
              </div>
            ) : null}
          </div>
        );
      }

      if (isEnergyAlignmentPage) {
        return renderEnergyAlignmentTemplate(parsed);
      }

      if (isActionRemediesPage) {
        return renderActionRemediesTemplate(parsed);
      }

      if (isFinalInsightsPage) {
        return renderFinalInsightsTemplate(parsed);
      }

      if (usesYearlyStyleTemplate) {
        return renderYearlyOrFavorableTemplate(parsed);
      }

      if (isStrategicOverviewPage) {
        const reserved = new Set(
          [coreInsight, naturalStrength, growthEdge, actionPath, keyTraits].filter(Boolean).map((item) => item!.key),
        );
        const remaining = parsed.filter((item) => !reserved.has(item.key));
        const compatibilityCard =
          remaining.find((item) =>
            /mobile|compat|compatible|compatibility|alignment|supportive/i.test(`${item.label} ${item.value}`),
          ) || remaining[0];
        const extraCards = remaining.filter((item) => item.key !== compatibilityCard?.key);

        return withMatrix(
          <div className="strategic-flow strategic-flow--executive">
            <div className="strategic-flow__top">
              <StrategicOverviewVisual
                report={report}
                title={compatibilityCard?.label || "Mobile Compatibility"}
                value={compatibilityCard?.value || "Supportive"}
              />

              <div className="strategic-flow-cards strategic-flow-cards--stack">
                {coreInsight ? (
                  <InfoCard
                    key={coreInsight.key}
                    title={coreInsight.label}
                    tone="accent"
                    className="life-intel-core"
                    lines={[coreInsight.value]}
                  />
                ) : null}
                {naturalStrength ? (
                  <InfoCard key={naturalStrength.key} title={naturalStrength.label} tone="soft" lines={[naturalStrength.value]} />
                ) : null}
                {growthEdge ? <InfoCard key={growthEdge.key} title={growthEdge.label} tone="soft" lines={[growthEdge.value]} /> : null}
                {actionPath ? (
                  <InfoCard
                    key={actionPath.key}
                    title={actionPath.label}
                    tone="default"
                    className="report-profile-action life-intel-action"
                    lines={[actionPath.value]}
                  />
                ) : null}
              </div>
            </div>

            {keyTraits ? (
              <InfoCard
                key={keyTraits.key}
                title={keyTraits.label}
                tone="soft"
                className={cx("life-intel-traits strategic-flow-traits", !extraCards.length && "strategic-flow-traits--stretch")}
                lines={[keyTraits.value]}
              />
            ) : null}

            {extraCards.length ? (
              <div className="strategic-flow-tail grid gap-3 md:grid-cols-2">
                {extraCards.map((item) => (
                  <InfoCard key={item.key} title={item.label} tone="soft" lines={[item.value]} />
                ))}
              </div>
            ) : null}
          </div>
        );
      }

      if (!isLifeIntelligencePage) {
        return withMatrix(
          <div className="report-fallback-grid grid gap-4 md:grid-cols-2">
            {parsed.map((item, idx) => {
              const interpretedValue = item.label ? resolveMetricMeaning(item.label, item.value || lines[idx], report) : item.value || lines[idx];
              return (
                <InfoCard
                  key={item.key}
                  title={item.label || `????? ????? ${idx + 1}`}
                  tone={idx === 0 ? "accent" : "soft"}
                  lines={[interpretedValue]}
                />
              );
            })}
          </div>
        );
      }

      const reserved = new Set(
        [coreInsight, naturalStrength, growthEdge, actionPath, keyTraits].filter(Boolean).map((item) => item!.key),
      );

      const remaining = parsed.filter((item) => !reserved.has(item.key));
      const numericMetrics = remaining
        .map((item) => ({ ...item, number: toNumber(item.value) }))
        .filter((item) => item.number !== undefined) as Array<{ key: string; label: string; value: string; number: number }>;
      const extraCards = remaining.filter((item) => toNumber(item.value) === undefined);

      const hasPremiumTemplate =
        Boolean(coreInsight || naturalStrength || growthEdge || actionPath || keyTraits || numericMetrics.length);

      if (!hasPremiumTemplate) {
        return withMatrix(
          <div className="report-fallback-grid grid gap-4 md:grid-cols-2">
            {parsed.map((item, idx) => {
              const interpretedValue = item.label ? resolveMetricMeaning(item.label, item.value || lines[idx], report) : item.value || lines[idx];
              return (
                <InfoCard
                  key={item.key}
                  title={item.label || `????? ????? ${idx + 1}`}
                  tone={idx === 0 ? "accent" : "soft"}
                  lines={[interpretedValue]}
                />
              );
            })}
          </div>
        );
      }

      if (isLifeIntelligencePage) {
        const balanceMetrics = numericMetrics.slice(0, 2);
        const detailMetrics = numericMetrics.slice(2);
        const lifeMetricCards = [...balanceMetrics, ...detailMetrics];
        return withMatrix(
          <div className="life-intel-layout">
            <div className="life-intel-scale-wrap">
              <div className="life-intel-balance-panel rounded-[24px] border border-[#c8a95f] bg-white/88 p-4">
                <LifeIntelligenceBalance metrics={balanceMetrics} />
              </div>
            </div>

            <div className="life-intel-story space-y-3">
              {coreInsight ? (
                <InfoCard
                  key={coreInsight.key}
                  title={coreInsight.label}
                  tone="accent"
                  className="life-intel-core"
                  lines={[coreInsight.value]}
                />
              ) : null}
              {naturalStrength ? (
                <InfoCard key={naturalStrength.key} title={naturalStrength.label} tone="soft" lines={[naturalStrength.value]} />
              ) : null}
              {growthEdge ? <InfoCard key={growthEdge.key} title={growthEdge.label} tone="soft" lines={[growthEdge.value]} /> : null}
              {actionPath ? (
                <InfoCard
                  key={actionPath.key}
                  title={actionPath.label}
                  tone="default"
                  className="report-profile-action life-intel-action"
                  lines={[actionPath.value]}
                />
              ) : null}
            </div>

            <div className="life-intel-tail">
              {keyTraits ? (
                <InfoCard
                  key={keyTraits.key}
                  title={keyTraits.label}
                  tone="soft"
                  className="life-intel-traits"
                  lines={[keyTraits.value]}
                />
              ) : null}

              {lifeMetricCards.length ? (
                <div className={cx("life-intel-metric-grid grid gap-3 md:grid-cols-2", !extraCards.length && "life-intel-metric-grid--stretch")}>
                  {lifeMetricCards.map((metric) => (
                    <InfoCard
                      key={`life-metric-${metric.key}`}
                      title={metric.label}
                      tone="soft"
                      lines={[resolveMetricMeaning(metric.label, metric.number, report)]}
                    />
                  ))}
                </div>
              ) : null}

              <div className="life-intel-extra grid gap-3 md:grid-cols-2">
                {extraCards.map((item) => (
                  <InfoCard key={item.key} title={item.label} tone="soft" lines={[item.value]} />
                ))}
              </div>
            </div>
          </div>
        );
      }

      return withMatrix(
        <div className="report-premium-grid grid gap-4 md:grid-cols-2">
          {coreInsight ? (
            <InfoCard
              key={coreInsight.key}
              title={coreInsight.label}
              tone="accent"
              className="report-premium-core md:row-span-2"
              lines={[coreInsight.value]}
              imageSrc={ASSETS.chakra}
            />
          ) : null}

          {naturalStrength ? (
            <InfoCard
              key={naturalStrength.key}
              title={naturalStrength.label}
              tone="soft"
              lines={[naturalStrength.value]}
              imageSrc={ASSETS.lotus}
            />
          ) : null}

          {actionPath ? (
            <InfoCard
              key={actionPath.key}
              title={actionPath.label}
              tone="soft"
              lines={[actionPath.value]}
              imageSrc={ASSETS.deities.mangal}
            />
          ) : null}

          {growthEdge ? (
            <InfoCard
              key={growthEdge.key}
              title={growthEdge.label}
              tone="soft"
              lines={[growthEdge.value]}
              imageSrc={ASSETS.deities.budh}
            />
          ) : null}

          {numericMetrics.length ? (
            <div className="report-premium-metric-panel rounded-[24px] border border-[#c9a75f] bg-white/86 p-4 md:row-span-2">
              <p className="mb-3 text-[24px] font-semibold uppercase tracking-[0.02em] text-[#132f53]">Your Key Traits</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {numericMetrics.slice(0, 4).map((metric) => (
                  <MetricRing key={metric.key} label={metric.label} value={metric.number} />
                ))}
              </div>
            </div>
          ) : null}

          {keyTraits ? (
            <InfoCard
              key={keyTraits.key}
              title={keyTraits.label}
              tone="soft"
              lines={[keyTraits.value]}
              imageSrc={ASSETS.deities.guru}
            />
          ) : null}

          {extraCards.map((item) => (
            <InfoCard
              key={item.key}
              title={item.label}
              tone="soft"
              lines={[item.value]}
              className="md:col-span-2"
            />
          ))}
        </div>
      );
    })()
  );
}

function SectionPage({
  section,
  index,
  report,
  pageNumber,
  totalPages,
}: {
  section: HindiSection;
  index: number;
  report: ReportResponse;
  pageNumber: number;
  totalPages: number;
}) {
  const llmOnly = Boolean(
    (report as any)?.content?.meta?.llm_only ||
      (report as any)?.content?.meta?.llmOnly ||
      (report as any)?.content?.llm_only,
  );
  const languageMode = String(
    report?.content?.meta?.language ||
      report?.content?.normalizedInput?.language ||
      report?.content?.input_normalized?.language ||
      report?.content?.deterministic?.normalizedInput?.language ||
      "hindi",
  ).toLowerCase();
  const premiumTitle = resolvePremiumSectionTitle(section.key, section.title);
  const normalizedSectionKey = SECTION_KEY_ALIAS_MAP[section.key] || section.key;
  void getSectionAccent(section, report);
  const isProfileSectionPage = normalizedSectionKey === "profile";
  const normalizedSectionPageClass = `report-section-page--${normalizedSectionKey.replace(/_/g, "-")}`;
  const pattern: "center" | "top" | "bottom" =
    index % 3 === 1 ? "center" : index % 3 === 2 ? "top" : "bottom";
  const normalizedSectionTitle = repairDisplayText(section.title || "").toLowerCase();

  const resolveTemplateType = (): SectionTemplateType => {
    const key = normalizedSectionKey.toLowerCase();
    if (key.includes("grid") || key.includes("tracker") || key.includes("impact")) return "grid";
    if (
      key.includes("visual") ||
      key.includes("lo_shu") ||
      key.includes("number_interaction") ||
      normalizedSectionTitle.includes("grid")
    ) {
      return "visual";
    }
    if (key.includes("summary") || key.includes("closing") || key.includes("next_steps")) return "summary";
    if (key.includes("recommendation") || key.includes("analysis") || key.includes("verdict")) return "analysis";
    return "insight";
  };

  const resolveTag = (type: SectionTemplateType) => {
    if (type === "visual") return "Energy Pattern";
    if (type === "grid") return "Analysis";
    if (type === "summary") return "Summary";
    if (type === "analysis") return "Recommendation";
    return "Core Insight";
  };

  const cleanedLines = (section.blocks || [])
    .map((item) => repairDisplayText(String(item || "").trim()))
    .filter((item) => item.length > 0);
  const parsedLines = cleanedLines.map((line) => parseLine(line));

  const summaryItems = parsedLines
    .filter((line) => String(line.label || "").trim() && String(line.value || "").trim())
    .slice(0, 8)
    .map((line) => ({
      label: repairDisplayText(line.label || ""),
      value: repairDisplayText(line.value || ""),
    }));

  const bodyText = parsedLines
    .filter((line) => !String(line.label || "").trim())
    .map((line) => repairDisplayText(line.value || ""))
    .filter(Boolean)
    .join(" ");

  const bullets = parsedLines
    .map((line) => repairDisplayText(line.value || line.label || ""))
    .filter((line) => line.length > 0)
    .slice(0, 6);

  const takeaways =
    summaryItems.slice(0, 2).map((item) => `${item.label}: ${item.value}`) ||
    bullets.slice(0, 2);

  const sectionTemplateData: ReportSectionTemplateData = {
    sectionNumber: String(index).padStart(2, "0"),
    title: cleanTitle(premiumTitle, index).replace(/^\d+\.\s*/, ""),
    subtitle: repairDisplayText(section.subtitle || ""),
    type: resolveTemplateType(),
    tag: resolveTag(resolveTemplateType()),
    languageMode,
    summaryItems,
    highlightValue: summaryItems[0]?.value || "",
    bodyTitle: summaryItems[0]?.label || "",
    bodyText,
    notes: bullets.slice(0, 3),
    bullets: bullets.slice(0, 5),
    takeaways: (takeaways.length ? takeaways : bullets).slice(0, 4),
    visualType: resolveTemplateType() === "visual" ? "matrix" : "none",
    pageClassName: cx(normalizedSectionPageClass, isProfileSectionPage && "report-section-page--profile-intel"),
    content: llmOnly ? null : <SectionContent section={section} report={report} />,
  };

  return (
    <ReportPage pattern={pattern} pageNumber={pageNumber} totalPages={totalPages}>
      {renderSectionPage(sectionTemplateData)}
    </ReportPage>
  );
}

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const originalTitleRef = useRef<string>("");
  useEffect(() => {
    if (!id) return;

    const fetchReport = async () => {
      try {
        const res = await API.get(`/reports/${id}`);
        setReport(res.data);
      } catch {
        setError("Failed to load report.");
        toast.error("Failed to load report");
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [id]);

  useEffect(() => {
    const handleAfterPrint = () => {
      if (originalTitleRef.current) {
        document.title = originalTitleRef.current;
      }
    };

    window.addEventListener("afterprint", handleAfterPrint);
    return () => {
      window.removeEventListener("afterprint", handleAfterPrint);
      if (originalTitleRef.current) {
        document.title = originalTitleRef.current;
      }
    };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.printPreview = "true";
    return () => {
      delete document.documentElement.dataset.printPreview;
    };
  }, []);

  const handlePrint = () => {
    const fullName = resolveReportName(report) || "Report";
    if (!originalTitleRef.current) {
      originalTitleRef.current = document.title;
    }
    document.title = fullName;
    window.print();
  };

  const llmOnly = Boolean((report as any)?.content?.meta?.llm_only || (report as any)?.content?.meta?.llmOnly);
  const sections: HindiSection[] = useMemo(
    () => {
      const legacySections = report?.content?.report_sections ?? [];

      const canonicalSections = report?.content?.sections ?? [];
      if (canonicalSections.length > 0) {
        const filtered = llmOnly
          ? canonicalSections.filter((section) => String(section?.sectionKey || "").toLowerCase() !== "cover_page")
          : canonicalSections;
        return filtered.map((section, index) => adaptCanonicalSection(section, index));
      }

      return [];
    },
    [report, llmOnly],
  );

  const printTotalPages = sections.length + 1;
  void PageHeader;
  void SectionPage;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#efe7d7] text-[#173a63]">
        <div className="text-lg font-medium">Loading report...</div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#efe7d7] px-6 text-center text-rose-700">
        {error || "Report not found."}
      </div>
    );
  }

  return (
    <>
      <div className="no-print text-[#173a63]">
        <div className="app-print-hidden sticky top-0 z-30 bg-transparent py-1.5">
          <div className="mx-auto w-[210mm] max-w-[calc(100vw-2rem)] border border-[#d8c49d] bg-[#fbf7ef]/95 px-3 py-3 shadow-[0_8px_20px_rgba(16,34,58,0.08)] backdrop-blur">
            <div className="flex flex-col items-center gap-3 text-center">
              <div className="min-w-0 w-full">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#9c7941]">
                  Printable Report View
                </p>
                <h1
                  title={report.title || "Life Signify Ank(अंक) AI Report"}
                  className="font-[var(--font-report-heading)] text-[clamp(1.45rem,2vw,2.05rem)] leading-tight text-[#173a63]"
                >
                  {report.title || "Life Signify Ank(अंक) AI Report"}
                </h1>
                <p className="mt-1 text-[11px] font-semibold text-[#9c7941]">
                  Tip: Enable “Background graphics” in your print dialog for full design fidelity.
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-2">
                <Link
                  to="/reports"
                  className="rounded-full border border-[#ccb07b] px-4 py-2 text-sm font-semibold text-[#173a63] transition hover:bg-white/80"
                >
                  Back to Reports
                </Link>
                <Link
                  to="/generate-report"
                  className="rounded-full border border-[#173a63] bg-[#173a63] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#1f4a7a]"
                >
                  Generate New
                </Link>
                <button
                  onClick={handlePrint}
                  className="rounded-full border border-[#c09b57] bg-[linear-gradient(180deg,#f6e4b8_0%,#e4c57f_100%)] px-5 py-2 text-sm font-semibold text-[#173a63] transition hover:brightness-105"
                >
                  Print
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <ReportPrintView
        report={report}
        sections={sections}
        coverPage={<CoverPage report={report} pageNumber={1} totalPages={printTotalPages} />}
      />
    </>
  );
}







