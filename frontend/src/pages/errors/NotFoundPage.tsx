import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center px-6">
      
      {/* Error Code */}
      <h1 className="text-6xl font-bold text-indigo-500">404</h1>

      {/* Title */}
      <h2 className="text-2xl font-semibold mt-4">
        Page Not Found
      </h2>

      {/* Description */}
      <p className="text-gray-400 mt-2 text-center max-w-md">
        The page you’re looking for doesn’t exist
        or may have been moved.
      </p>

      {/* Button */}
      <Link
        to="/dashboard"
        className="mt-6 bg-indigo-600 hover:bg-indigo-500 px-6 py-2 rounded-lg font-semibold transition"
      >
        Back to Dashboard
      </Link>

    </div>
  );
}