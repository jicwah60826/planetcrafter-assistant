using System.Text.Json;
using System.Text.RegularExpressions;
using PlanetCrafterAssistant.Models;

namespace PlanetCrafterAssistant.Services
{
    public class RecipeService
    {
        private readonly List<Recipe> _recipes;

        public RecipeService(IWebHostEnvironment env)
        {
            var recipesPath = Path.Combine(env.WebRootPath, "data", "recipes.json");
            var json = File.ReadAllText(recipesPath);
            var allRecipes =
                JsonSerializer.Deserialize<List<Recipe>>(
                    json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                ) ?? new List<Recipe>();

            var exclusionPatterns = LoadExclusionPatterns(env);
            _recipes = allRecipes.Where(r => !IsExcluded(r.Name, exclusionPatterns)).ToList();
        }

        public List<Recipe> GetAll() => _recipes;

        public Recipe? GetByName(string name) =>
            _recipes.FirstOrDefault(
                r => string.Equals(r.Name, name, StringComparison.OrdinalIgnoreCase)
            );

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
