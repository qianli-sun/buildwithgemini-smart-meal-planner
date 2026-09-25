# My agent: SmartMeal Planner
One-liner: A conversational agent that helps a busy remote professional plan flexible, healthy daily meals adapted to their daily schedule and consolidate weekend grocery lists with a catalog of nutritious recipes and pantry staples.

Tool coverage:
- Memory: Dietary preferences (healthy focus), dietary restrictions/allergies, favorite cuisines, foods to avoid, kitchen gear, and per-day schedule preferences (e.g. default time budgets, with adaptability between quick <15–30 min sprint lunches and relaxed 45+ min cook sessions).
- Tools: Search and filter healthy recipes by dynamic time tiers (express <15m, standard <30m, relaxed/leisure 45m+) and meal type; swap meals on the fly based on daily availability; generate aggregated grocery lists.
- Catalog/UI: Recipe cards with prep/cook time badges and tags, interactive weekly planner table with customizable daily time budgets, and categorized grocery checklist table.
- Image gen: Appetizing, high-quality dish preview photos of proposed recipes.
- Sandbox: Calculate nutritional totals (calories, macros) across flexible meal plans, and scale ingredient quantities accurately for weekend grocery shopping.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): code sandbox for nutrition calculations and grocery quantity scaling, Cloud Trace for latency tracking, and optional calendar integration to auto-detect busy meeting days
