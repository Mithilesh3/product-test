import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { useAuth } from "../../context/AuthContext";

const SuperAdminLoginPage = () => {
  const { loginSuperAdmin, user } = useAuth();
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      navigate("/dashboard");
    }
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    if (!identifier || !password) {
      toast.error("Please enter super admin login ID and password");
      return;
    }

    setLoading(true);
    try {
      await loginSuperAdmin(identifier, password);
      toast.success("Welcome, Super Admin");
      navigate("/dashboard");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Invalid super admin credentials");
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
          <h1 className="text-3xl font-bold">Super Admin Login</h1>
          <p className="text-gray-400 mt-2">Restricted operations access</p>
        </div>

        <div>
          <label className="text-sm text-gray-400">Login ID (email/mobile)</label>
          <input
            type="text"
            autoFocus
            className="w-full mt-1 p-3 bg-gray-800 rounded-lg border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="superadmin@domain.com"
          />
        </div>

        <div>
          <label className="text-sm text-gray-400">Password</label>
          <input
            type="password"
            className="w-full mt-1 p-3 bg-gray-800 rounded-lg border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full p-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-semibold transition disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Login as Super Admin"}
        </button>

        <div className="text-center text-sm text-gray-400">
          Back to{" "}
          <Link to="/login" className="text-indigo-400 hover:underline">
            User Login
          </Link>
        </div>
      </form>
    </div>
  );
};

export default SuperAdminLoginPage;
