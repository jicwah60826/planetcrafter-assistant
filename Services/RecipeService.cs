using System.Text.Json;
using PlanetCrafterAssistant.Models;

namespace PlanetCrafterAssistant.Services
{
    public class RecipeService
    {
        private readonly List<Recipe> _recipes;

        public RecipeService(IWebHostEnvironment env)
        {
            var path = Path.Combine(env.WebRootPath, "data", "recipes.json");
            var json = File.ReadAllText(path);
            _recipes =
                JsonSerializer.Deserialize<List<Recipe>>(
                    json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                ) ?? new List<Recipe>();
        }

        public List<Recipe> GetAll() => _recipes;

        public Recipe? GetByName(string name) =>
            _recipes.FirstOrDefault(
                r => string.Equals(r.Name, name, StringComparison.OrdinalIgnoreCase)
            );
    }
}
