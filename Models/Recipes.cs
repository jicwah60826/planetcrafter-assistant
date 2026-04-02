namespace PlanetCrafterAssistant.Models
{
    public class Recipe
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public string Category { get; set; } // Raw, Resource, Toxicity, Machine
        public List<Ingredient> Ingredients { get; set; } = new();

        /// <summary>
        /// Derives the expected icon filename from the item name.
        /// e.g. "Super Alloy" → "super_alloy"
        /// </summary>
        public string IconSlug => Name?.ToLower().Replace(" ", "_") ?? "default";
    }

    public class Ingredient
    {
        public string Name { get; set; }
        public int Quantity { get; set; }
    }
}
