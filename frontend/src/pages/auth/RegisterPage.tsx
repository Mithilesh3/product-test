import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import toast from "react-hot-toast";

import API from "../../services/api";
import billingService from "../../services/billingService";

declare global {
  interface Window {
    Razorpay: any;
  }
}

interface RegisterResponse {
  registration_pending: boolean;
  mobile_number: string;
  kyc_order: {
    id: string;
    amount: number;
    currency: string;
    description: string;
    provider?: string;
    checkout_url?: string | null;
  };
}

const RegisterPage = () => {
  const navigate = useNavigate();
  const KYC_MOBILE_KEY = "lsn_kyc_mobile";

  const [form, setForm] = useState({
    full_name: "",
    mobile_number: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const returnedOrderId = params.get("phonepe_order_id");
    const returnedMobile = params.get("mobile") || localStorage.getItem(KYC_MOBILE_KEY);
    if (!returnedOrderId || !returnedMobile) {
      return;
    }

    const verifyReturnedKyc = async () => {
      setLoading(true);
      const verifyToast = toast.loading("Verifying KYC payment...");
      try {
        console.info("[KYC] Calling verify-kyc API (PhonePe return flow)", {
          mobile: returnedMobile,
          order_id: returnedOrderId,
        });
        toast("Calling KYC verification API...", { icon: "ℹ️" });
        await API.post("/users/register/verify-kyc", {
          mobile_number: returnedMobile,
          order_id: returnedOrderId,
        });
        toast.success("Registration complete. Please login with mobile number and password.", {
          id: verifyToast,
        });
        const nextUrl = window.location.pathname;
        window.history.replaceState({}, document.title, nextUrl);
        localStorage.removeItem(KYC_MOBILE_KEY);
        navigate("/login");
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || "KYC verification failed", {
          id: verifyToast,
        });
        const nextUrl = window.location.pathname;
        window.history.replaceState({}, document.title, nextUrl);
        localStorage.removeItem(KYC_MOBILE_KEY);
      } finally {
        setLoading(false);
      }
    };

    void verifyReturnedKyc();
  }, [navigate]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const validatePassword = (password: string) => {
    if (password.length < 6) {
      return "Password must be at least 6 characters";
    }
    return null;
  };

  const getRegisterErrorMessage = (error: unknown) => {
    if (!axios.isAxiosError(error)) {
      return "Registration failed";
    }

    const payload = error.response?.data as
      | { detail?: string; message?: string }
      | undefined;

    return (
      payload?.detail ||
      payload?.message ||
      (error.response
        ? "Unable to register with provided details"
        : "Backend is unreachable. Please check server status.")
    );
  };

  const openKycPayment = async (registration: RegisterResponse) => {
    if (registration?.kyc_order?.provider === "phonepe") {
      if (!registration?.kyc_order?.checkout_url) {
        throw new Error("PhonePe checkout URL missing");
      }
      localStorage.setItem(KYC_MOBILE_KEY, registration.mobile_number);
      const redirectUrl = new URL(registration.kyc_order.checkout_url);
      redirectUrl.searchParams.set("mobile", registration.mobile_number);
      window.location.href = redirectUrl.toString();
      return;
    }

    if (!window.Razorpay) {
      throw new Error("Payment gateway unavailable. Please refresh and try again.");
    }

    const razorpayKey = await billingService.getRazorpayKey();

    const options = {
      key: razorpayKey,
      amount: registration.kyc_order.amount,
      currency: registration.kyc_order.currency,
      name: "Life Signify NumAI",
      description: "KYC Verification Fee (Rs. 1, Non-refundable)",
      order_id: registration.kyc_order.id,
      handler: async function (response: any) {
        const verifyToast = toast.loading("Verifying KYC payment...");
        try {
          console.info("[KYC] Calling verify-kyc API (Razorpay handler)", {
            mobile: registration.mobile_number,
            order_id: response.razorpay_order_id,
          });
          toast("Calling KYC verification API...", { icon: "ℹ️" });
          await API.post("/users/register/verify-kyc", {
            mobile_number: registration.mobile_number,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          });

          toast.success("Registration complete. Please login with mobile number and password.", {
            id: verifyToast,
          });
          navigate("/login");
        } catch (error: any) {
          toast.error(error?.response?.data?.detail || "KYC verification failed", {
            id: verifyToast,
          });
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
        color: "#4F46E5",
      },
    };

    const razorpay = new window.Razorpay(options);
    razorpay.on("payment.failed", function (response: any) {
      const reason =
        response?.error?.description ||
        response?.error?.reason ||
        "Payment failed. Please retry KYC payment.";
      toast.error(reason);
      setLoading(false);
    });
    razorpay.open();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    const browserLocale = navigator.language || "en-IN";
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kolkata";
    const localeCountry = browserLocale.includes("-")
      ? browserLocale.split("-")[1]?.toUpperCase()
      : undefined;

    const payload = {
      full_name: form.full_name.trim(),
      mobile_number: form.mobile_number.trim(),
      password: form.password,
      signup_source: "web_signup",
      signup_locale: browserLocale,
      signup_timezone: timezone,
      signup_country: localeCountry,
    };

    if (!payload.full_name || !payload.mobile_number || !payload.password) {
      toast.error("Full name, mobile number and password are required");
      return;
    }

    const passwordError = validatePassword(payload.password);
    if (passwordError) {
      toast.error(passwordError);
      return;
    }

    setLoading(true);
    const loadingToast = toast.loading("Creating account...");

    try {
      const response = await API.post<RegisterResponse>("/users/register", payload);
      toast.success("Registration saved. Complete Rs. 1 KYC payment.", {
        id: loadingToast,
      });
      await openKycPayment(response.data);
    } catch (error) {
      toast.error(getRegisterErrorMessage(error), {
        id: loadingToast,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 text-white p-6">
      <form
        onSubmit={handleSubmit}
        className="bg-gray-900 p-8 rounded-2xl w-full max-w-md shadow-xl space-y-6"
      >
        <div className="text-center">
          <h1 className="text-3xl font-bold">Create Account</h1>
          <p className="text-gray-400 mt-2">Register and complete Rs. 1 KYC verification</p>
        </div>

        <div>
          <label className="text-sm text-gray-400">Full Name</label>
          <input
            name="full_name"
            value={form.full_name}
            onChange={handleChange}
            className="w-full mt-1 p-3 bg-gray-800 rounded-lg border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Your full name"
          />
        </div>

        <div>
          <label className="text-sm text-gray-400">Mobile Number</label>
          <input
            name="mobile_number"
            value={form.mobile_number}
            onChange={handleChange}
            className="w-full mt-1 p-3 bg-gray-800 rounded-lg border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="10 digit mobile"
          />
        </div>

        <div>
          <label className="text-sm text-gray-400">Password</label>
          <div className="relative">
            <input
              name="password"
              type={showPassword ? "text" : "password"}
              value={form.password}
              onChange={handleChange}
              className="w-full mt-1 p-3 bg-gray-800 rounded-lg border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 pr-12"
              placeholder="........"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-400 hover:text-white"
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full p-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-semibold transition disabled:opacity-50"
        >
          {loading ? "Processing..." : "Register"}
        </button>

        <p className="text-xs text-gray-500">
          Registration includes a Rs. 1 non-refundable payment for KYC verification.
        </p>

        <div className="text-center text-sm text-gray-400">
          Already have an account?{" "}
          <Link to="/login" className="text-indigo-400 hover:underline">
            Login
          </Link>
        </div>
      </form>
    </div>
  );
};

export default RegisterPage;
