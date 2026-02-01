/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        minsa: {
          blue: '#00539C',
          red: '#E10600',
          light: '#F5F5F5',
        },
        brand: {
          pink: {
            50: '#FCE8EB',
            100: '#FAE1E5',
            200: '#FFD1DC',
            500: '#FF8DA1',
            600: '#FF5E7B',
          }
        }
      }
    },
  },
  plugins: [],
}
