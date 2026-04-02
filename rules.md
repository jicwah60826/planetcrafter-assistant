# Commit Notes Reference

A running log of commit messages for this project. Copy and paste into SourceTree as needed.

---

## [Current] Separate recipe data from app logic via RecipeService and recipes.json

- Move all hardcoded recipe/ingredient data out of HomeController into wwwroot/data/recipes.json
- Add Services/RecipeService.cs to load and cache recipes from JSON at startup
- Register RecipeService as a singleton in Program.cs
- Update HomeController to inject and use RecipeService instead of GetRecipes()