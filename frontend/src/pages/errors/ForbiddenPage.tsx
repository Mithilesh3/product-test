import { Link } from "react-router-dom";

export default function ForbiddenPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center px-6">
      
      {/* Error Code */}
      <h1 className="text-6xl font-bold text-red-500">403</h1>

      {/* Title */}
      <h2 className="text-2xl font-semibold mt-4">
        Access Forbidden
      </h2>

      {/* Description */}
      <p className="text-gray-400 mt-2 text-center max-w-md">
        You don’t have permission to access this page.
        Please upgrade your plan or contact support if you believe this is a mistake.
      </p>

      {/* Action Buttons */}
      <div className="mt-6 flex gap-4">
        <Link
          to="/dashboard"
          className="bg-indigo-600 hover:bg-indigo-500 px-5 py-2 rounded-lg font-semibold transition"
        >
          Go to Dashboard
        </Link>

        <Link
          to="/upgrade"
          className="border border-gray-700 hover:border-gray-500 px-5 py-2 rounded-lg font-semibold transition"
        >
          Upgrade Plan
        </Link>
      </div>

    </div>
  );
}