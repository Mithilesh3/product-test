import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

const LoginPage = () => {
  const { login, user } = useAuth();
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
      toast.error("Please enter mobile/email and password");
      return;
    }

    setLoading(true);
    try {
      await login(identifier, password);
      toast.success("Welcome back");
      navigate("/dashboard");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Invalid credentials");
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
          <h1 className="text-3xl font-bold">Life Signify Login</h1>
          <p className="text-gray-400 mt-2">Access your intelligence dashboard</p>
        </div>

        <div>
          <label className="text-sm text-gray-400">Mobile Number or Email</label>
          <input
            type="text"
            autoFocus
            className="w-full mt-1 p-3 bg-gray-800 rounded-lg border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="10 digit mobile or email"
          />
        </div>

        <div>
          <label className="text-sm text-gray-400">Password</label>
          <input
            type="password"
            className="w-full mt-1 p-3 bg-gray-800 rounded-lg border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="********"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full p-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-semibold transition disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Login"}
        </button>

        <div className="text-center text-sm text-gray-400">
          Do not have an account?{" "}
          <Link to="/register" className="text-indigo-400 hover:underline">
            Register
          </Link>
        </div>

        <div className="text-center text-sm text-gray-500">
          <Link to="/super-admin/login" className="text-amber-400 hover:underline">
            Super Admin Login
          </Link>
        </div>
      </form>
    </div>
  );
};

export default LoginPage;
