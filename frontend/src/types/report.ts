export interface CoreMetrics {
  risk_band?: string;
  confidence_score?: number;
  karma_pressure_index?: number;
  life_stability_index?: number;
  dharma_alignment_score?: number;
  emotional_regulation_index?: number;
  financial_discipline_index?: number;
}

export interface DeterministicNumbers {
  mulank?: number;
  bhagyank?: number;
  name_energy?: number;
  mobile_total?: number;
  email_energy?: number;
  personal_year?: number;
}

export interface InputNormalized {
  name?: string;
  mobile?: string;
  email?: string;
  date_of_birth?: string;
  birth_place?: string;
  gender?: string;
  current_problem?: string;
  report_format?: string;
  target_year?: number;
}

export interface CanonicalNormalizedInput {
  fullName?: string;
  dateOfBirth?: string;
  gender?: string;
  mobileNumber?: string;
  email?: string;
  focusArea?: string;
  currentProblem?: string;
  city?: string;
  country?: string;
}

export interface LoShuGrid {
  grid_counts?: Record<string, number>;
  present?: number[];
  missing?: number[];
  repeating?: number[];
  repeating_counts?: Record<string, number>;
}

export interface LuckyNumbersBundle {
  primary?: number[];
  support?: number[];
  favorable_dates?: number[];
}

export interface ColorAlignmentBundle {
  favorable?: string[];
  caution?: string[];
}

export interface RemedyBundle {
  anchor?: string;
  mantra?: string;
  repetition?: string;
  donation?: string;
  behaviour?: string;
}

export interface PersonalYearBundle {
  theme?: string;
  opportunities?: string;
  caution?: string;
  action_direction?: string;
}

export interface MobileProfileBundle {
  classification?: string;
  summary?: string;
  fit_note?: string;
}

export interface CompatibilityBundle {
  score?: number;
  label?: string;
}

export interface ClosingBundle {
  life_theme?: string;
  key_challenge?: string;
  final_guidance?: string;
}

export interface DeterministicBundle {
  numbers?: DeterministicNumbers;
  lo_shu?: LoShuGrid;
  lucky_numbers?: LuckyNumbersBundle;
  color_alignment?: ColorAlignmentBundle;
  remedy?: RemedyBundle;
  personal_year?: PersonalYearBundle;
  mobile_profile?: MobileProfileBundle;
  mobile_life_compatibility?: CompatibilityBundle;
  closing?: ClosingBundle;
  priority_flags?: string[];
  problem_context?: {
    category?: string;
    tone_family?: string;
  };
}

export interface HindiSection {
  order: number;
  key: string;
  title: string;
  subtitle?: string;
  layout?: string;
  blocks: string[];
}

export interface CanonicalReportSection {
  sectionKey: string;
  sectionTitle: string;
  summary: string;
  keyStrength: string;
  keyRisk: string;
  practicalGuidance: string;
  loadedEnergies: string[];
  scoreHighlights: Array<{
    label: string;
    value: string;
  }>;
}

export interface ReportContent {
  meta?: {
    plan_tier?: string;
    section_count?: number;
    language?: string;
    generated_at?: string;
  };
  input_normalized?: InputNormalized;
  normalizedInput?: CanonicalNormalizedInput;
  core_metrics?: CoreMetrics;
  deterministic?: DeterministicBundle;
  section_selector?: {
    format?: string;
    selected_section_count?: number;
  };
  sections?: CanonicalReportSection[];
  report_sections?: HindiSection[];
}

export interface ReportResponse {
  id: number;
  title: string;
  content: ReportContent;
  engine_version: string;
  confidence_score: number;
  created_at: string;
  updated_at?: string | null;
}
