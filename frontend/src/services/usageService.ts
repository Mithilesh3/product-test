import API from "./api";

export interface UsageResponse {
  reports_used: number;
  reports_limit: number;
  reports_remaining: number;
  subscription_plan: string;
}

export const getUsage = async (): Promise<UsageResponse> => {
  const res = await API.get("/reports/metrics/usage");

  return {
    reports_used: res.data.reports_used ?? res.data.reports_used_this_month ?? 0,
    reports_limit: res.data.plan_limit ?? res.data.monthly_limit ?? 0,
    reports_remaining: res.data.reports_remaining || 0,
    subscription_plan: res.data.subscription_plan || "none",
  };
};
