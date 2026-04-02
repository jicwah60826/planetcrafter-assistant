# Commit Notes Reference

A running log of commit messages for this project. Copy and paste into SourceTree as needed.

---

## [Current] Add craftedIn and recyclerYields data to recipe details pane

- Add CraftedIn and RecyclerYields properties to Models/Recipes.cs
- Add craftedIn and recyclerYields fields to all entries in wwwroot/data/recipes.json
- Add getCraftedInHtml() helper in Recipes.cshtml to render CRAFTED IN section
- Show crafting station and optional Recycling Machine row in details pane
- Add .pane-row--station, .pane-row--recycle, .pane-row-note styles to site.css

---

## [2026-04-01] Show unlock conditions in recipe details pane

- Add UnlockCondition model (Stage, Threshold, Unit) to Models/Recipes.cs
- Add unlockCondition field to all entries in wwwroot/data/recipes.json
- Render UNLOCKS badge in the right-hand details pane in Recipes.cshtml
- Add stageIcons map and getUnlockHtml() helper in Recipes.cshtml JS
- Add .pane-unlock, .pane-unlock--always, .pane-unlock-icon CSS rules to site.css

---

## [2026-04-01] Expand recipes.json with full Planet Crafter item set

- Add Raw materials: Sulfur, Zeolite, Osmium, Pulsar Quartz, Astrofossil, Ice, Lirma Seed, Phytoplankton A & B
- Add Resource items: Osmium Rod, Explosive Powder, Fertilizer, Bacteria Sample, Water Filter, Rocket Engine, Toilet
- Add Machine items: Ore Extractors T1–T3, Gas Extractor, Water Collector, Atmosphere Analyser, Biodome, Bioreactor, Heaters T1–T3, Atmospheric Condenser, Oxygen Generator
- Add new categories: Rocket, Energy, Storage, Equipment, Structure, Automation

---

## [2026-04-01] Separate recipe data from app logic via RecipeService and recipes.json

- Move all hardcoded recipe/ingredient data out of HomeController into wwwroot/data/recipes.json
- Add Services/RecipeService.cs to load and cache recipes from JSON at startup
- Register RecipeService as a singleton in Program.cs
- Update HomeController to inject and use RecipeService instead of GetRecipes()