import { createContext, useContext, useEffect, useState } from "react";
import { getUsage } from "../services/usageService";
import { useAuth } from "./AuthContext";

interface Usage {
  reports_used: number;
  reports_limit: number;
  reports_remaining: number;
}

const PLAN_LIMITS: Record<string, number> = {
  basic: 1,
  standard: 5,
  enterprise: 21,
};

const UsageContext = createContext<{
  usage: Usage | null;
  refreshUsage: () => Promise<void>;
} | null>(null);

export const UsageProvider = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  const [usage, setUsage] = useState<Usage | null>(null);

  const loadUsage = async () => {
    if (!user) {
      setUsage(null);
      return;
    }

    try {
      const data = await getUsage();
      setUsage(data);
    } catch {
      if (user.subscription) {
        const reportsUsed = user.subscription.reports_used || 0;
        const reportsLimit =
          PLAN_LIMITS[user.subscription.plan_name?.toLowerCase()] ?? 0;

        setUsage({
          reports_used: reportsUsed,
          reports_limit: reportsLimit,
          reports_remaining: Math.max(reportsLimit - reportsUsed, 0),
        });
      } else {
        setUsage({
          reports_used: 0,
          reports_limit: 0,
          reports_remaining: 0,
        });
      }
    }
  };

  useEffect(() => {
    void loadUsage();
  }, [user]);

  return (
    <UsageContext.Provider value={{ usage, refreshUsage: loadUsage }}>
      {children}
    </UsageContext.Provider>
  );
};

export const useUsage = () => {
  const ctx = useContext(UsageContext);

  if (!ctx) {
    throw new Error("useUsage must be inside UsageProvider");
  }

  return ctx;
};
