/**
 * Vercel Speed Insights initialization
 * This script initializes Speed Insights for performance tracking
 */
import { injectSpeedInsights } from './speed-insights.mjs';

// Initialize Speed Insights
injectSpeedInsights({
  debug: false, // Set to true for debugging in development
});
