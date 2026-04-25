/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./App.{js,jsx,ts,tsx}", "./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        muted: "#64748b",
        surface: "#f8fafc",
        brand: "#2563eb",
      },
    },
  },
  plugins: [],
};
