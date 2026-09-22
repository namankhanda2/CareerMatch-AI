/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        ink: {
          50: "#f4f7fb",
          100: "#e8eef6",
          700: "#1e3a5f",
          800: "#152a46",
          900: "#0d1b2e",
        },
        brand: {
          50: "#eef7ff",
          500: "#2563eb",
          600: "#1d4ed8",
        },
      },
      boxShadow: {
        card: "0 10px 40px -18px rgba(15, 23, 42, 0.28)",
      },
    },
  },
  plugins: [],
};
