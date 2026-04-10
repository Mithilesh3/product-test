import API from "./api";

let cachedRazorpayKey: string | null = null;
let cachedGatewayProvider: string | null = null;

const openBlobInNewTab = (blob: Blob) => {
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
};

const triggerBlobDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
};

const billingService = {
  getPaymentConfig: async () => {
    const res = await API.get("/payments/public-config");
    const provider = res.data?.provider || "razorpay";
    cachedGatewayProvider = provider;
    const key = res.data?.razorpay_key_id || import.meta.env.VITE_RAZORPAY_KEY;
    if (provider === "razorpay") {
      cachedRazorpayKey = key || null;
    }
    return { provider, razorpay_key_id: key || null };
  },

  getRazorpayKey: async () => {
    if (cachedGatewayProvider === "phonepe") {
      throw new Error("Razorpay not active");
    }
    if (cachedRazorpayKey) {
      return cachedRazorpayKey;
    }
    const config = await billingService.getPaymentConfig();
    const key = config.razorpay_key_id;
    if (!key) {
      throw new Error("Razorpay key not configured");
    }
    cachedRazorpayKey = key;
    return key;
  },

  getPlans: async () => {
    const res = await API.get("/payments/plans");
    return res.data;
  },

  getPaymentHistory: async () => {
    const res = await API.get("/payments/history");
    return res.data;
  },

  createOrder: async (planName: string) => {
    const res = await API.post("/payments/create-order", {
      plan: planName,
    });
    return res.data;
  },

  verifyPayment: async (paymentData: any) => {
    const res = await API.post("/payments/verify", paymentData);
    return res.data;
  },

  getInvoice: async (paymentId: number) => {
    const res = await API.get(`/payments/invoice/${paymentId}`);
    return res.data;
  },

  viewInvoice: async (paymentId: number) => {
    const res = await API.get(`/payments/invoice/${paymentId}/view`, {
      responseType: "blob",
    });
    openBlobInNewTab(res.data);
  },

  downloadInvoice: async (paymentId: number) => {
    const res = await API.get(`/payments/invoice/${paymentId}/download`, {
      responseType: "blob",
    });
    const invoiceNo = res.headers?.["x-invoice-number"];
    const filename = invoiceNo ? `invoice-${invoiceNo}.html` : `invoice-${paymentId}.html`;
    triggerBlobDownload(res.data, filename);
  },
};

export default billingService;
