import type { Dispatch, SetStateAction } from "react";

export type LifeFocusValue =
  | "finance_debt"
  | "career_growth"
  | "business_decision"
  | "relationship"
  | "health_stability"
  | "emotional_confusion"
  | "general_alignment"
  | "";

export type RiskToleranceValue = "low" | "moderate" | "high" | "";

export interface IdentityData {
  full_name?: string;
  gender?: string;
  email?: string;
  mobile_number?: string;
  country_of_residence?: string;
  date_of_birth?: string;
}

export interface BirthDetailsData {
  date_of_birth?: string;
  time_of_birth?: string;
  birthplace_city?: string;
  birthplace_country?: string;
}

export interface FocusData {
  life_focus?: LifeFocusValue;
}

export interface ContactData {
  mobile_number?: string;
}

export interface FinancialData {
  monthly_income?: number;
  savings_ratio?: number;
  debt_ratio?: number;
  risk_tolerance?: RiskToleranceValue;
}

export interface EmotionalData {
  anxiety_level?: number;
  decision_confusion?: number;
  impulse_control?: number;
  emotional_stability?: number;
}

export interface BusinessHistoryData {
  [key: string]: string | number | boolean | undefined;
}

export interface HealthData {
  [key: string]: string | number | boolean | undefined;
}

export interface CalibrationData {
  [key: string]: string | number | boolean | undefined;
}

export interface ReportFormData {
  identity: IdentityData;
  birth_details: BirthDetailsData;
  focus: FocusData;
  contact: ContactData;
  current_problem: string;
  financial: FinancialData;
  emotional: EmotionalData;
  business_history: BusinessHistoryData;
  health: HealthData;
  calibration: CalibrationData;
}

export interface ReportStepProps {
  formData: ReportFormData;
  setFormData: Dispatch<SetStateAction<ReportFormData>>;
  next: () => void;
  prev: () => void;
  submit: () => Promise<void>;
  plan: string;
  submitting: boolean;
}
