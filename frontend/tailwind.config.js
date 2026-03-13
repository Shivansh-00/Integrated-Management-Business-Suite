module.exports = {
  content: ["./index.html", "./static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        imbs: {
          midnight: "#0c1220",
          ocean: "#13203b",
          mint: "#00c4a7",
          cloud: "#e8efff",
        },
      },
      boxShadow: {
        glass: "0 20px 55px rgba(0, 0, 0, 0.35)",
      },
    },
  },
  plugins: [],
};
