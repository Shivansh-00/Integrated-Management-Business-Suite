window.renderAIInsights = function (insights) {
  return insights.map((i) => `• ${i.title}: ${i.summary}`).join("\n");
};
