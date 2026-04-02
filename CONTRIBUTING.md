# Contributing Guidelines

## Project Standards

### Data / Logic Separation
- All game data (recipes, descriptions, categories, ingredients) must live in `wwwroot/data/recipes.json`, not in C# source files.
- The application loads this file at startup via `RecipeService` (see `Services/RecipeService.cs`), which caches the deserialized list for the lifetime of the application.
- Controllers must never contain hardcoded game data. Use injected services instead.

## Guidelines
- Follow existing C# coding style (PascalCase for public members, `var` for local variables).
- Register new services in `Program.cs` using the appropriate lifetime (`AddSingleton` for stateless data services).