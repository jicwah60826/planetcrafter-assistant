namespace PlanetCrafterAssistant.Models
{
    public class Tip
    {
        public string Id { get; set; } = string.Empty;
        public string Title { get; set; } = string.Empty;
        public string Category { get; set; } = string.Empty;
        public string Summary { get; set; } = string.Empty;
        public string Content { get; set; } = string.Empty;
        public string Emoji { get; set; } = "💡";
    }
}
