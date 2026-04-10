import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import billingService from "../../services/billingService";
import toast from "react-hot-toast";

interface Plan {
  name: string;
  price: number;
  reports_limit: number | string;
}

interface PaymentHistory {
  id: number;
  amount: number;
  amount_inr?: number;
  status: string;
  plan_name?: string;
  payment_reference?: string;
  created_at: string;
}

declare global {
  interface Window {
    Razorpay: any;
  }
}

function normalizePlanName(planName?: string | null) {
  const raw = (planName || "").toLowerCase().trim();
  if (!raw) return "";
  if (raw === "pro") return "standard";
  if (raw === "premium") return "enterprise";
  return raw;
}

export default function BillingPage() {
  const { user, refreshUser } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [payments, setPayments] = useState<PaymentHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [upgradingPlan, setUpgradingPlan] = useState<string | null>(null);
  const [invoiceLoadingId, setInvoiceLoadingId] = useState<number | null>(null);

  const loadBillingData = async () => {
    try {
      const [plansRes, paymentRes] = await Promise.all([
        billingService.getPlans(),
        billingService.getPaymentHistory(),
      ]);
      setPlans(plansRes || []);
      setPayments(paymentRes || []);
    } catch {
      toast.error("Failed to load billing data");
      setPlans([]);
      setPayments([]);
    } finally {
      setLoading(false);
    }
  };

  const activeSubscriptionPlan = normalizePlanName(user?.subscription?.plan_name);
  const hasActiveSubscription = Boolean(user?.subscription?.is_active && activeSubscriptionPlan);
  const currentPlan = hasActiveSubscription ? activeSubscriptionPlan : "none";

  useEffect(() => {
    void loadBillingData();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const phonepeOrderId = params.get("phonepe_order_id");
    if (!phonepeOrderId) {
      return;
    }

    const verifyReturnedPayment = async () => {
      const verifyToast = toast.loading("Verifying returned payment...");
      try {
        await billingService.verifyPayment({ order_id: phonepeOrderId });
        await refreshUser();
        await loadBillingData();
        toast.success("Payment verified successfully", { id: verifyToast });
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || "Payment verification failed", { id: verifyToast });
      } finally {
        params.delete("phonepe_order_id");
        const nextQuery = params.toString();
        const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}`;
        window.history.replaceState({}, document.title, nextUrl);
      }
    };

    void verifyReturnedPayment();
  }, [refreshUser]);

  const formatAmount = (payment: PaymentHistory) => {
    if (typeof payment.amount_inr === "number") {
      return payment.amount_inr.toFixed(2);
    }
    // Legacy fallback: when API amount is returned in paise.
    const amount = Number(payment.amount || 0);
    return amount > 5000 || amount <= 500
      ? (amount / 100).toFixed(2)
      : amount.toFixed(2);
  };

  const handleUpgrade = async (planName: string) => {
    const normalizedPlan = normalizePlanName(planName);
    if (upgradingPlan || (hasActiveSubscription && currentPlan === normalizedPlan)) {
      return;
    }

    setUpgradingPlan(normalizedPlan);

    try {
      const order = await billingService.createOrder(planName);
      if (order?.provider === "phonepe") {
        if (!order.checkout_url) {
          throw new Error("PhonePe checkout URL missing");
        }
        window.location.href = order.checkout_url;
        return;
      }

      if (!window.Razorpay) {
        throw new Error("Payment gateway unavailable. Please refresh and try again.");
      }

      const razorpayKey = await billingService.getRazorpayKey();

      const options = {
        key: razorpayKey,
        amount: order.amount,
        currency: "INR",
        order_id: order.id,
        name: "LifeSignify",
        description: `${planName} Subscription`,
        handler: async function (response: any) {
          try {
            await billingService.verifyPayment(response);
            await refreshUser();
            await loadBillingData();
            toast.success("Subscription upgraded successfully");
          } catch {
            toast.error("Payment verification failed");
          } finally {
            setUpgradingPlan(null);
          }
        },
        modal: {
          ondismiss: function () {
            setUpgradingPlan(null);
          },
        },
        theme: {
          color: "#6366f1",
        },
      };

      const razor = new window.Razorpay(options);
      razor.open();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Payment failed");
      setUpgradingPlan(null);
    }
  };

  const handleViewInvoice = async (paymentId: number) => {
    setInvoiceLoadingId(paymentId);
    try {
      await billingService.viewInvoice(paymentId);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to open invoice");
    } finally {
      setInvoiceLoadingId(null);
    }
  };

  const handleDownloadInvoice = async (paymentId: number) => {
    setInvoiceLoadingId(paymentId);
    try {
      await billingService.downloadInvoice(paymentId);
      toast.success("Invoice downloaded");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to download invoice");
    } finally {
      setInvoiceLoadingId(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        Loading Billing...
      </div>
    );
  }

  return (
    <div className="space-y-6 md:space-y-8">
      <div>
        <h1 className="text-2xl font-bold md:text-3xl">Subscription and Billing</h1>
        <p className="text-gray-400 mt-1">
          Manage your subscription and payments
        </p>
      </div>

      <div className="rounded-xl bg-gray-900 p-4 shadow-md sm:p-6">
        <p className="text-gray-400 text-sm">Current Plan</p>
        <p className="mt-2 text-2xl font-bold">
          {hasActiveSubscription ? currentPlan.toUpperCase() : "NO ACTIVE PLAN"}
        </p>
        {!hasActiveSubscription ? (
          <p className="mt-2 text-sm text-amber-300">
            KYC payment (Rs 1) does not activate subscription. Please choose a plan below.
          </p>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {plans.map((plan) => {
          const normalizedPlan = normalizePlanName(plan.name);
          const isCurrent = hasActiveSubscription && currentPlan === normalizedPlan;
          const isProcessing = upgradingPlan === normalizedPlan;

          return (
            <div
              key={plan.name}
              className="bg-gray-900 p-6 rounded-xl shadow-md flex flex-col justify-between"
            >
              <div>
                <h2 className="text-xl font-semibold">{plan.name}</h2>

                <p className="text-3xl font-bold mt-2">
                  Rs {plan.price}
                </p>

                <ul className="mt-4 space-y-2 text-gray-300 text-sm">
                  <li>
                    {plan.reports_limit} AI Report
                    {typeof plan.reports_limit === "number" && plan.reports_limit > 1 ? "s" : ""} included
                  </li>
                </ul>
              </div>

              {isCurrent ? (
                <div className="mt-6 text-emerald-400 font-semibold text-center">
                  Current Plan
                </div>
              ) : (
                <button
                  onClick={() => handleUpgrade(plan.name)}
                  disabled={Boolean(upgradingPlan)}
                  className="mt-6 bg-indigo-600 hover:bg-indigo-500 p-3 rounded-lg font-semibold transition disabled:opacity-50"
                >
                  {isProcessing ? "Processing..." : hasActiveSubscription ? "Upgrade" : "Activate Plan"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      <div className="rounded-xl bg-gray-900 p-4 shadow-md sm:p-6">
        <h2 className="text-xl font-semibold mb-4">Payment History</h2>

        {payments.length === 0 ? (
          <p className="text-gray-400">No payments found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="py-2">Date</th>
                <th className="py-2">Plan</th>
                <th className="py-2">Amount</th>
                <th className="py-2">Status</th>
                <th className="py-2">Reference</th>
                <th className="py-2">Invoice</th>
              </tr>
            </thead>
              <tbody>
                {payments.map((payment) => {
                  const isPaid = payment.status === "paid";
                  const isInvoiceBusy = invoiceLoadingId === payment.id;

                  return (
                    <tr key={payment.id} className="border-b border-gray-800">
                      <td className="py-2">
                        {new Date(payment.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-2 capitalize">{payment.plan_name || "-"}</td>
                      <td className="py-2">Rs {formatAmount(payment)}</td>
                      <td
                        className={`py-2 ${
                          isPaid ? "text-emerald-400" : "text-yellow-400"
                        }`}
                      >
                        {payment.status}
                      </td>
                      <td className="py-2 text-xs text-gray-300 break-all">
                        {payment.payment_reference || "-"}
                      </td>
                      <td className="py-2">
                        {isPaid ? (
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => handleViewInvoice(payment.id)}
                              disabled={isInvoiceBusy}
                              className="px-3 py-1 rounded border border-indigo-500 text-indigo-300 hover:bg-indigo-500/20 disabled:opacity-50"
                            >
                              View
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDownloadInvoice(payment.id)}
                              disabled={isInvoiceBusy}
                              className="px-3 py-1 rounded border border-emerald-500 text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50"
                            >
                              Download
                            </button>
                          </div>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
