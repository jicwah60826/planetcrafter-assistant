using System.Text.Json;
using PlanetCrafterAssistant.Models;

namespace PlanetCrafterAssistant.Services
{
    public class TipsService
    {
        private readonly List<Tip> _tips;

        public TipsService(IWebHostEnvironment env)
        {
            var path = Path.Combine(env.WebRootPath, "data", "tips.json");
            var json = File.ReadAllText(path);
            _tips =
                JsonSerializer.Deserialize<List<Tip>>(
                    json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true }
                ) ?? new List<Tip>();
        }

        public List<Tip> GetAll() => _tips;
    }
}
