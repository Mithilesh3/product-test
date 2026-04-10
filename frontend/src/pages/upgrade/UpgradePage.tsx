import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../../services/api";
import billingService from "../../services/billingService";
import { useAuth } from "../../context/AuthContext";
import toast from "react-hot-toast";

declare global {
  interface Window {
    Razorpay: any;
  }
}

export default function UpgradePage() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const currentRawPlan = (user?.organization?.plan || user?.subscription?.plan_name || "basic").toLowerCase();
  const currentPlan = currentRawPlan === "pro" ? "standard" : currentRawPlan === "premium" ? "enterprise" : currentRawPlan;

  useEffect(() => {
    const queryParams = new URLSearchParams(window.location.search);
    const returnedPhonepeOrder = queryParams.get("phonepe_order_id");
    if (!returnedPhonepeOrder) return;

    const verifyReturn = async () => {
      setLoading(true);
      const verifyToast = toast.loading("Verifying returned payment...");
      try {
        await API.post("/payments/verify", { order_id: returnedPhonepeOrder });
        await refreshUser();
        toast.success("Subscription activated", { id: verifyToast });
        window.history.replaceState({}, document.title, window.location.pathname);
        navigate("/dashboard");
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || "Payment verification failed", { id: verifyToast });
        window.history.replaceState({}, document.title, window.location.pathname);
      } finally {
        setLoading(false);
      }
    };

    void verifyReturn();
  }, [navigate, refreshUser]);

  const handleUpgrade = async () => {
    if (loading || currentPlan === "standard") return;

    setLoading(true);

    try {
      const orderRes = await API.post("/payments/create-order", {
        plan: "standard",
      });

      const { id, amount, currency, provider, checkout_url } = orderRes.data;
      if (provider === "phonepe") {
        if (!checkout_url) {
          throw new Error("PhonePe checkout URL missing");
        }
        window.location.href = checkout_url;
        return;
      }

      const razorpayKey = await billingService.getRazorpayKey();

      const options = {
        key: razorpayKey,
        amount,
        currency,
        name: "Life Signify NumAI",
        description: "Standard Plan (5 report credits)",
        order_id: id,

        handler: async function (response: any) {
          const verifyToast = toast.loading("Verifying payment...");

          try {
            await API.post("/payments/verify", {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });

            await refreshUser();
            toast.success("Subscription activated", { id: verifyToast });
            navigate("/dashboard");
          } catch (error: any) {
            toast.error(
              error?.response?.data?.detail?.[0]?.msg ||
                error?.response?.data?.detail ||
                "Payment verification failed",
              { id: verifyToast },
            );
          } finally {
            setLoading(false);
          }
        },

        modal: {
          ondismiss: function () {
            setLoading(false);
          },
        },

        theme: {
          color: "#6366F1",
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail?.[0]?.msg ||
          error?.response?.data?.detail ||
          "Failed to create order",
      );
      setLoading(false);
    }
  };

  const isStandard = currentPlan === "standard";

  return (
    <div className="flex min-h-[70vh] items-center justify-center py-4">
      <div className="w-full max-w-md space-y-6 rounded-xl bg-gray-900 p-5 text-center sm:p-8 md:p-10">
        <h1 className="text-2xl font-bold md:text-3xl">Upgrade to Standard</h1>

        <p className="text-gray-400">Unlock full AI strategic analysis and premium insights.</p>

        <div className="bg-gray-800 p-6 rounded-xl">
          <p className="text-xl font-semibold">Rs 499</p>
          <p className="text-sm text-gray-300 mt-1">Includes 5 AI report credits</p>
          <p className="text-sm text-gray-400 mt-2">Cancel anytime</p>
        </div>

        <button
          onClick={handleUpgrade}
          disabled={loading || isStandard}
          className="bg-emerald-600 hover:bg-emerald-500 w-full py-3 rounded-lg font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isStandard ? "Already on Standard Plan" : loading ? "Processing..." : "Upgrade Now"}
        </button>

        {isStandard && <div className="text-emerald-400 font-semibold">You are already on Standard Plan</div>}
      </div>
    </div>
  );
}
