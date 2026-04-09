using System.Text.Json;
using System.Text.RegularExpressions;
using PlanetCrafterAssistant.Models;

namespace PlanetCrafterAssistant.Services
{
    public class RecipeService
    {
        private readonly List<Recipe> _recipes;
        private readonly List<CraftStation> _stations;

        public RecipeService(IWebHostEnvironment env)
        {
            var recipesPath = Path.Combine(env.WebRootPath, "data", "recipes.json");
            var json = File.ReadAllText(recipesPath);
            var allRecipes =
                JsonSerializer.Deserialize<List<Recipe>>(
                    json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                ) ?? new List<Recipe>();

            var nameOverrides = LoadNameOverrides(env);
            ApplyNameOverrides(allRecipes, nameOverrides);

            var exclusionPatterns = LoadExclusionPatterns(env);
            _recipes = allRecipes.Where(r => !IsExcluded(r.Name, exclusionPatterns)).ToList();

            _stations = LoadCraftStations(env);
        }

        public List<Recipe> GetAll() => _recipes;

        public Recipe? GetByName(string name) =>
            _recipes.FirstOrDefault(
                r => string.Equals(r.Name, name, StringComparison.OrdinalIgnoreCase)
            );

        public List<CraftStation> GetAllStations() => _stations;

        public CraftStation? GetStation(string displayName) =>
            _stations.FirstOrDefault(
                s => string.Equals(s.DisplayName, displayName, StringComparison.OrdinalIgnoreCase)
            );

        // ── Station helpers ────────────────────────────────────

        private static List<CraftStation> LoadCraftStations(IWebHostEnvironment env)
        {
            var path = Path.Combine(env.WebRootPath, "data", "craftStations.json");
            if (!File.Exists(path))
                return new List<CraftStation>();

            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            if (!doc.RootElement.TryGetProperty("stations", out var stationsEl))
                return new List<CraftStation>();

            return JsonSerializer.Deserialize<List<CraftStation>>(
                    stationsEl.GetRawText(),
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                ) ?? new List<CraftStation>();
        }

        // ── Name override helpers ──────────────────────────────

        private static Dictionary<string, string> LoadNameOverrides(IWebHostEnvironment env)
        {
            var path = Path.Combine(env.WebRootPath, "data", "name_overrides.json");
            if (!File.Exists(path))
                return new Dictionary<string, string>();

            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            if (!doc.RootElement.TryGetProperty("items", out var itemsEl))
                return new Dictionary<string, string>();

            var overrides = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var entry in itemsEl.EnumerateArray())
            {
                var from = entry.TryGetProperty("from", out var f) ? f.GetString() : null;
                var to = entry.TryGetProperty("to", out var t) ? t.GetString() : null;
                if (!string.IsNullOrWhiteSpace(from) && !string.IsNullOrWhiteSpace(to))
                    overrides[from] = to;
            }
            return overrides;
        }

        private static void ApplyNameOverrides(
            List<Recipe> recipes,
            Dictionary<string, string> overrides
        )
        {
            if (overrides.Count == 0)
                return;

            foreach (var recipe in recipes)
            {
                if (overrides.TryGetValue(recipe.Name, out var newName))
                    recipe.Name = newName;

                foreach (var ingredient in recipe.Ingredients)
                {
                    if (overrides.TryGetValue(ingredient.Name, out var newIngredientName))
                        ingredient.Name = newIngredientName;
                }
            }
        }

        // ── Exclusion helpers ──────────────────────────────────

        private static List<string> LoadExclusionPatterns(IWebHostEnvironment env)
        {
            var path = Path.Combine(env.WebRootPath, "data", "exclusions.json");
            if (!File.Exists(path))
                return new List<string>();

            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            if (!doc.RootElement.TryGetProperty("rules", out var rulesEl))
                return new List<string>();

            return rulesEl
                .EnumerateArray()
                .Select(e => e.GetString() ?? string.Empty)
                .Where(s => !string.IsNullOrWhiteSpace(s))
                .ToList();
        }

        private static bool IsExcluded(string name, List<string> patterns)
        {
            foreach (var pattern in patterns)
            {
                if (MatchesPattern(name, pattern))
                    return true;
            }
            return false;
        }

        /// <summary>
        /// Supports wildcard patterns using * as a prefix, suffix, or both.
        /// e.g. "*Hatched" | "Hatched*" | "*Hatched*" | "Exact Name"
        /// Matching is case-insensitive.
        /// </summary>
        private static bool MatchesPattern(string name, string pattern)
        {
            // Convert the simple wildcard pattern to a regex
            var escaped = Regex.Escape(pattern).Replace(@"\*", ".*");
            return Regex.IsMatch(name, $"^{escaped}$", RegexOptions.IgnoreCase);
        }
    }
}
