import { useTheme } from "../../context/ThemeContext";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="px-3 py-2 text-sm rounded-lg bg-gray-800 dark:bg-gray-700 text-white"
    >
      {theme === "dark" ? "☀ Light Mode" : "🌙 Dark Mode"}
    </button>
  );
}