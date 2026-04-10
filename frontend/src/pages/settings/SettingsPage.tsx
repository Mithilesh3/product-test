import { useAuth } from "../../context/AuthContext";

export default function SettingsPage() {
  const { user } = useAuth();

  const rawPlan = (user?.subscription?.plan_name || user?.organization?.plan || "free").toLowerCase();
  const plan = rawPlan === "pro" ? "standard" : rawPlan === "premium" ? "enterprise" : rawPlan;
  const isActive = user?.subscription?.is_active;

  return (
    <div className="space-y-6 md:space-y-8">
      <div>
        <h1 className="text-2xl font-bold md:text-3xl">Settings</h1>
        <p className="text-gray-400 mt-1">Manage your account preferences</p>
      </div>

      <div className="rounded-xl bg-gray-900 p-4 shadow-md sm:p-6">
        <h2 className="text-xl font-semibold mb-4">Account Info</h2>

        <div className="space-y-3 text-gray-300">
          <p>
            <span className="text-gray-400">Email:</span> {user?.email || "-"}
          </p>

          <p>
            <span className="text-gray-400">Plan:</span>{" "}
            <span
              className={`font-semibold ml-1 ${
                plan === "standard"
                  ? "text-emerald-400"
                  : plan === "enterprise"
                    ? "text-purple-400"
                    : "text-gray-300"
              }`}
            >
              {plan.toUpperCase()}
            </span>
          </p>

          {isActive && <p className="text-sm text-green-400">Active Subscription</p>}
        </div>
      </div>

      <div className="rounded-xl bg-gray-900 p-4 shadow-md sm:p-6">
        <h2 className="text-xl font-semibold mb-2">Preferences</h2>
        <p className="text-gray-400 text-sm">
          Notification settings, password updates, and integrations will be available here.
        </p>
      </div>
    </div>
  );
}
