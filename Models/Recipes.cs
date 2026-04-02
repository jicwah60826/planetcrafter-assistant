namespace PlanetCrafterAssistant.Models
{
    public class Recipe
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public string Category { get; set; } // Raw, Resource, Toxicity, Machine
        public List<Ingredient> Ingredients { get; set; } = new();
    }

    public class Ingredient
    {
        public string Name { get; set; }
        public int Quantity { get; set; }
    }
}
