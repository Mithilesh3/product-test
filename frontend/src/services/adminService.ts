import API from "./api";

export type AdminAnalytics = {
  total_users: number;
  total_reports: number;
  total_organizations: number;
  active_subscriptions: number;
};

export type OrgUser = {
  id: number;
  email: string | null;
  full_name?: string | null;
  mobile_number?: string | null;
  role: "admin" | "manager" | "user" | string;
  tenant_id?: number;
  organization_name?: string | null;
  organization_plan?: string | null;
  kyc_verified?: boolean;
  is_blocked?: boolean;
  signup_source?: string | null;
  signup_ip?: string | null;
  signup_city?: string | null;
  signup_country?: string | null;
  signup_locale?: string | null;
  signup_timezone?: string | null;
  created_at: string | null;
};

export type InviteUserResponse = {
  message: string;
  temporary_password: string;
};

export type ManualCreateUserPayload = {
  full_name?: string;
  mobile_number?: string;
  email?: string;
  password?: string;
  role: "admin" | "manager" | "user";
  organization_name?: string;
  organization_plan?: string;
  kyc_verified?: boolean;
};

export type ManualCreateUserResponse = {
  message: string;
  id: number;
  tenant_id: number;
  email?: string | null;
  mobile_number?: string | null;
  role: string;
  generated_password: string;
};

/* ==============================
   ADMIN ANALYTICS (Dashboard)
============================== */
export const fetchAdminAnalytics = async (): Promise<AdminAnalytics> => {
  const res = await API.get("/admin/analytics");
  return res.data;
};

/* ==============================
   ORGANIZATION USERS
============================== */
export const fetchOrgUsers = async (): Promise<OrgUser[]> => {
  const res = await API.get("/users/org-users");
  return res.data;
};

/* ==============================
   SUPER ADMIN - GLOBAL USERS
============================== */
export const fetchAllRegisteredUsers = async (): Promise<OrgUser[]> => {
  const res = await API.get("/admin/users/all");
  return res.data;
};

/* ==============================
   INVITE USER
============================== */
export const inviteUser = async (
  email: string,
  role: string
): Promise<InviteUserResponse> => {
  const res = await API.post("/users/invite", {
    email,
    role,
  });
  return res.data;
};

/* ==============================
   DELETE USER
============================== */
export const deleteUser = async (userId: number): Promise<{ message: string }> => {
  const res = await API.delete(`/users/delete-user/${userId}`);
  return res.data;
};

/* ==============================
   UPDATE USER ROLE
============================== */
export const updateUserRole = async (
  userId: number,
  newRole: string
): Promise<{ message: string }> => {
  const res = await API.put(
    `/users/update-user-role/${userId}?new_role=${newRole}`
  );
  return res.data;
};

/* ==============================
   SUPER ADMIN - MANUAL CREATE USER
============================== */
export const createManualUser = async (
  payload: ManualCreateUserPayload
): Promise<ManualCreateUserResponse> => {
  const res = await API.post("/admin/users/manual-create", payload);
  return res.data;
};

/* ==============================
   SUPER ADMIN - BLOCK / UNBLOCK
============================== */
export const setUserBlocked = async (
  userId: number,
  blocked: boolean
): Promise<{ message: string; user_id: number; is_blocked: boolean }> => {
  const res = await API.put(`/admin/users/${userId}/block?blocked=${blocked}`);
  return res.data;
};

/* ==============================
   SUPER ADMIN - KNOWLEDGE STUDIO
============================== */
export type KnowledgeAsset = {
  id: number;
  title: string | null;
  status: string;
  approval_status?: string | null;
  approved_at?: string | null;
  domain?: string | null;
  source_type: string;
  language: string | null;
  created_at: string | null;
  has_updates: boolean;
};

export const fetchKnowledgeAssets = async (): Promise<KnowledgeAsset[]> => {
  const res = await API.get("/admin/knowledge/assets");
  return res.data;
};

export const uploadKnowledgeAsset = async (formData: FormData) => {
  const res = await API.post("/admin/knowledge/assets", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const processKnowledgeAsset = async (assetId: number) => {
  const res = await API.post(`/admin/knowledge/assets/${assetId}/process`);
  return res.data;
};

export const applyKnowledgeAsset = async (assetId: number, notes?: string) => {
  const res = await API.post(`/admin/knowledge/assets/${assetId}/apply`, {
    consent: true,
    notes: notes || undefined,
  });
  return res.data;
};

export const rejectKnowledgeAsset = async (assetId: number, reason?: string) => {
  const res = await API.post(`/admin/knowledge/assets/${assetId}/reject`, {
    reason: reason || undefined,
  });
  return res.data;
};
