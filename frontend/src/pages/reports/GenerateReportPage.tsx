import { isAxiosError } from "axios";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { City } from "country-state-city";

import API from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import {
  buildReportSubmitPayload,
  createInitialReportFormState,
  planRequiredFields,
  planValidationSchemas,
  planVisibleFields,
  type ReportFieldKey,
  type ReportFormState,
  type ReportPlanKey,
} from "../../config/reportPlanForm";

interface ValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
}

interface StructuredDetail {
  message?: string;
  plan?: string;
  fields?: string[];
}

interface BackendErrorResponse {
  detail?: string | ValidationIssue[] | StructuredDetail;
}

type FieldControl = "input" | "select" | "datalist" | "city-select";

const PLAN_ORDER: Record<ReportPlanKey, number> = {
  BASIC: 1,
  STANDARD: 2,
  ENTERPRISE: 3,
};

const normalizeSubscriptionPlan = (planName?: string | null): ReportPlanKey | null => {
  const normalized = (planName || "").toLowerCase().trim();
  if (!normalized) return null;
  if (normalized === "basic") return "BASIC";
  if (normalized === "standard" || normalized === "pro") return "STANDARD";
  if (normalized === "enterprise" || normalized === "premium") return "ENTERPRISE";
  return null;
};

const canUsePlanBySubscription = (activePlan: ReportPlanKey | null, candidate: ReportPlanKey): boolean => {
  if (!activePlan) return true;
  return PLAN_ORDER[candidate] <= PLAN_ORDER[activePlan];
};

const fieldMeta: Record<
  ReportFieldKey,
  {
    label: string;
    placeholder: string;
    type?: "text" | "date" | "email" | "number";
    control?: FieldControl;
    options?: Array<{ value: string; label: string }>;
  }
> = {
  fullName: { label: "Full Name", placeholder: "Enter full name" },
  nameVariations: { label: "Name Variations", placeholder: "e.g. Jay | Jai | J. Prakash" },
  dateOfBirth: { label: "Date of Birth", placeholder: "", type: "date" },
  birthTime: { label: "Birth Time (Optional)", placeholder: "e.g. 06:45" },
  gender: {
    label: "Gender",
    placeholder: "Select gender",
    control: "select",
    options: [
      { value: "male", label: "Male" },
      { value: "female", label: "Female" },
      { value: "other", label: "Other" },
    ],
  },
  mobileNumber: { label: "Mobile Number", placeholder: "Enter mobile number" },
  email: { label: "Email", placeholder: "Enter email", type: "email" },
  businessName: { label: "Business/Brand Name", placeholder: "Optional business or brand name" },
  signatureStyle: { label: "Signature Style", placeholder: "Optional signature style" },
  focusArea: { label: "Focus Area", placeholder: "career_growth / finance_debt / general_alignment" },
  language: { label: "Language", placeholder: "hindi / english / hinglish" },
  occupation: { label: "Occupation", placeholder: "Enter occupation" },
  relationshipStatus: { label: "Relationship Status", placeholder: "single/married" },
  concernPrimary: {
    label: "Primary Challenge (Optional)",
    placeholder: "e.g. consistency (default: consistency)",
  },
  concernSecondary: { label: "Secondary Concern", placeholder: "Optional secondary concern" },
  incomeRangeMonthly: { label: "Monthly Income Range", placeholder: "e.g. 50000" },
  stressLevel: { label: "Stress Level (1-10)", placeholder: "e.g. 6" },
  workMode: { label: "Work Mode", placeholder: "job/business/hybrid" },
  maritalStatus: { label: "Marital Status", placeholder: "single/married" },
  industry: { label: "Industry", placeholder: "Enter industry" },
  employmentType: { label: "Employment Type", placeholder: "full-time/consultant/business owner" },
  incomeRangeAnnual: { label: "Annual Income Range", placeholder: "e.g. 1200000" },
  debtRange: { label: "Debt Range", placeholder: "e.g. 15" },
  goal1: { label: "Goal 1", placeholder: "Primary goal" },
  goal2: { label: "Goal 2", placeholder: "Secondary goal" },
  goal3: { label: "Goal 3", placeholder: "Third goal" },
  challenge1: { label: "Challenge 1", placeholder: "Top challenge" },
  challenge2: { label: "Challenge 2", placeholder: "Second challenge" },
  challenge3: { label: "Challenge 3", placeholder: "Third challenge" },
  reportEmphasis: { label: "Report Emphasis", placeholder: "strategic/correction/decision" },
  healthConcerns: { label: "Health Concerns", placeholder: "Optional health concerns" },
  city: {
    label: "Birthplace City",
    placeholder: "Select city",
    control: "city-select",
  },
  birthCountry: { label: "Birthplace Country", placeholder: "Optional (default India)" },
  socialHandle: { label: "Social Handle", placeholder: "Optional social handle" },
  domainHandle: { label: "Domain Handle", placeholder: "Optional domain handle" },
  residenceNumber: { label: "Residence Number", placeholder: "Optional residence number" },
  vehicleNumber: { label: "Vehicle Number", placeholder: "Optional vehicle number" },
  spiritualPreference: { label: "Spiritual Preference", placeholder: "optional" },
  willingnessToChange: {
    label: "Willingness To Change",
    placeholder: "Select willingness",
    control: "select",
    options: [
      { value: "undecided", label: "Undecided" },
      { value: "yes", label: "Yes" },
      { value: "no", label: "No" },
    ],
  },
};

export default function GenerateReportPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [formState, setFormState] = useState<ReportFormState>(() =>
    createInitialReportFormState(user?.mobile_number || "", user?.full_name || "", user?.email || ""),
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const activePlan = useMemo(
    () => (user?.subscription?.is_active ? normalizeSubscriptionPlan(user?.subscription?.plan_name) : null),
    [user?.subscription?.is_active, user?.subscription?.plan_name],
  );
  const planLockedBySubscription = Boolean(activePlan);
  const allowedPlans = useMemo(
    () =>
      (["BASIC", "STANDARD", "ENTERPRISE"] as ReportPlanKey[]).filter((plan) =>
        canUsePlanBySubscription(activePlan, plan),
      ),
    [activePlan],
  );

  const selectedPlan = formState.plan;
  const visibleFields = useMemo(() => planVisibleFields[selectedPlan], [selectedPlan]);
  const requiredFields = useMemo(() => new Set(planRequiredFields[selectedPlan]), [selectedPlan]);
  const indiaCities = useMemo(() => {
    const cityRows = City.getCitiesOfCountry("IN") || [];
    const names = cityRows
      .map((cityRow) => String(cityRow?.name || "").trim())
      .filter(Boolean);
    return Array.from(new Set(names)).sort((left, right) => left.localeCompare(right, "en-IN"));
  }, []);

  const onPlanChange = (plan: ReportPlanKey) => {
    if (!canUsePlanBySubscription(activePlan, plan)) {
      toast.error(`Your active plan is ${activePlan}. You can generate ${activePlan} and lower-tier reports.`);
      return;
    }
    setFormState((prev) => ({ ...prev, plan }));
    setErrors({});
  };

  const onFieldChange = (key: ReportFieldKey, value: string) => {
    setFormState((prev) => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    if (!activePlan) return;
    setFormState((prev) => (prev.plan === activePlan ? prev : { ...prev, plan: activePlan }));
  }, [activePlan]);

  const validate = () => {
    const schema = planValidationSchemas[selectedPlan];
    const result = schema.safeParse(formState);
    if (result.success) {
      setErrors({});
      return true;
    }

    const nextErrors: Record<string, string> = {};
    for (const issue of result.error.issues) {
      const key = String(issue.path[0] || "");
      nextErrors[key] = issue.message;
    }
    setErrors(nextErrors);
    return false;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error("Please fix validation errors");
      return;
    }

    setSubmitting(true);
    try {
      const payload = buildReportSubmitPayload(formState);
      const res = await API.post("/reports/generate-ai-report", payload);
      const reportId = res?.data?.id;
      toast.success("Report generated successfully");
      navigate(reportId ? `/reports/${reportId}` : "/reports");
    } catch (error: unknown) {
      const axiosError = isAxiosError<BackendErrorResponse>(error) ? error : null;
      if (axiosError?.code === "ECONNABORTED") {
        toast.error("Report generation timed out. Please retry once.");
      } else if (axiosError?.response?.status === 422) {
        const details = axiosError.response.data?.detail;
        if (Array.isArray(details)) {
          const message = details
            .map((issue) => {
              const location = Array.isArray(issue.loc) ? issue.loc.join(" -> ") : "field";
              return `${location}: ${issue.msg ?? "Invalid value"}`;
            })
            .join("\n");
          toast.error(message || "Invalid input data");
        } else if (typeof details === "string") {
          toast.error(details || "Invalid input data");
        } else if (details && typeof details === "object") {
          const fieldList = Array.isArray(details.fields) && details.fields.length
            ? ` (${details.fields.join(", ")})`
            : "";
          toast.error(`${details.message || "Invalid input data"}${fieldList}`);
        } else {
          toast.error("Invalid input data");
        }
      } else if (axiosError?.response?.status === 403) {
        const detail = axiosError.response.data?.detail;
        toast.error(typeof detail === "string" ? detail : "Plan upgrade required");
      } else {
        toast.error("Something went wrong");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
        <h1 className="text-2xl font-bold text-white">Generate Report</h1>
        <p className="text-gray-400 mt-1">Single-page plan-aware form</p>

        <div className="mt-6">
          <label className="text-sm text-gray-300">Plan</label>
          {planLockedBySubscription ? (
            <p className="text-xs text-emerald-300 mt-1">
              Active plan: {activePlan}. You can generate {allowedPlans.join(", ")} reports.
            </p>
          ) : null}
          <div className="mt-2 flex flex-wrap gap-2">
            {(["BASIC", "STANDARD", "ENTERPRISE"] as ReportPlanKey[]).map((plan) => (
              <button
                key={plan}
                type="button"
                onClick={() => onPlanChange(plan)}
                disabled={!canUsePlanBySubscription(activePlan, plan)}
                className={`px-4 py-2 rounded-lg border text-sm font-semibold ${
                  selectedPlan === plan
                    ? "bg-indigo-600 border-indigo-500 text-white"
                    : "bg-gray-800 border-gray-700 text-gray-300"
                } disabled:opacity-50`}
              >
                {plan === "ENTERPRISE" ? "PREMIUM" : plan}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          {visibleFields.map((fieldKey) => {
            const meta = fieldMeta[fieldKey];
            const control = meta.control || "input";
            const commonClassName =
              "w-full mt-1 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500";
            return (
              <div key={fieldKey}>
                <label className="text-sm text-gray-300">
                  {meta.label}
                  {requiredFields.has(fieldKey) ? <span className="text-rose-400"> *</span> : null}
                </label>
                {control === "select" ? (
                  <select
                    value={formState[fieldKey] || ""}
                    onChange={(event) => onFieldChange(fieldKey, event.target.value)}
                    className={commonClassName}
                  >
                    <option value="" disabled>
                      {meta.placeholder}
                    </option>
                    {(meta.options || []).map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : control === "city-select" ? (
                  <select
                    value={formState[fieldKey] || ""}
                    onChange={(event) => onFieldChange(fieldKey, event.target.value)}
                    className={commonClassName}
                  >
                    <option value="">{meta.placeholder}</option>
                    {indiaCities.map((cityName) => (
                      <option key={cityName} value={cityName}>
                        {cityName}
                      </option>
                    ))}
                  </select>
                ) : control === "datalist" ? (
                  <>
                    <input
                      type={meta.type || "text"}
                      list="india-city-options"
                      value={formState[fieldKey] || ""}
                      onChange={(event) => onFieldChange(fieldKey, event.target.value)}
                      placeholder={meta.placeholder}
                      className={commonClassName}
                    />
                    <datalist id="india-city-options">
                      {indiaCities.map((cityName) => (
                        <option key={cityName} value={cityName} />
                      ))}
                    </datalist>
                  </>
                ) : (
                  <input
                    type={meta.type || "text"}
                    value={formState[fieldKey] || ""}
                    onChange={(event) => onFieldChange(fieldKey, event.target.value)}
                    placeholder={meta.placeholder}
                    className={commonClassName}
                  />
                )}
                {errors[fieldKey] ? <p className="text-xs text-rose-400 mt-1">{errors[fieldKey]}</p> : null}
              </div>
            );
          })}
        </div>

        <button
          type="button"
          disabled={submitting}
          onClick={handleSubmit}
          className="mt-8 w-full p-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-semibold transition disabled:opacity-50"
        >
          {submitting
            ? "Generating Report..."
            : selectedPlan === "BASIC"
              ? "Generate Basic Report"
              : selectedPlan === "STANDARD"
                ? "Generate Standard Report"
                : "Generate Premium Report"}
        </button>
        {submitting ? (
          <div className="mt-4 rounded-lg border border-indigo-500/30 bg-indigo-500/10 p-3 text-sm text-indigo-100">
            <div className="flex items-center gap-3">
              <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-indigo-300 border-t-transparent" />
              <div>
                <p className="font-semibold">Report is generating. Please wait...</p>
                <p className="text-indigo-200/80">This may take up to 30-90 seconds depending on plan and AI response time.</p>
              </div>
            </div>
          </div>
        ) : null}
      </div>
      {submitting ? (
        <div className="fixed inset-0 z-40 bg-gray-950/60 backdrop-blur-[1px] flex items-center justify-center px-4">
          <div className="w-full max-w-md rounded-2xl border border-indigo-500/40 bg-gray-900/95 p-6 text-center shadow-2xl">
            <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-indigo-300 border-t-transparent" />
            <h3 className="text-lg font-bold text-white">Generating Your Report</h3>
            <p className="mt-2 text-sm text-indigo-200">
              We are analyzing your inputs and preparing personalized sections. Please keep this page open.
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
