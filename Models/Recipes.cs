namespace PlanetCrafterAssistant.Models
{
    public class Recipe
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public string Category { get; set; } // Raw, Resource, Toxicity, Machine, Rocket, Energy, etc.
        public List<Ingredient> Ingredients { get; set; } = new();
        public UnlockCondition? UnlockCondition { get; set; }

        /// <summary>
        /// The machine in which this item is crafted.
        /// e.g. "Crafting Table", "Biolab", "DNA Manipulator"
        /// Null for raw materials that cannot be crafted.
        /// </summary>
        public string? CraftedIn { get; set; }

        /// <summary>
        /// When true, this item's ingredients can be recovered one at a time
        /// using the in-game Recycling Machine.
        /// </summary>
        public bool RecyclerYields { get; set; }

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

    /// <summary>
    /// Describes the terraforming threshold required to unlock a blueprint.
    /// e.g. Stage = "Heat", Threshold = 100.00, Unit = "nK"
    /// </summary>
    public class UnlockCondition
    {
        /// <summary>
        /// The terraforming index that must be reached.
        /// e.g. "Heat", "Pressure", "Oxygen", "Biomass", "Plants", "Insects", "Animals"
        /// </summary>
        public string Stage { get; set; }

        /// <summary>
        /// The numeric value that must be reached.
        /// </summary>
        public double Threshold { get; set; }

        /// <summary>
        /// The display unit for the threshold value.
        /// e.g. "nK", "µPa", "ppm", "g"
        /// </summary>
        public string Unit { get; set; }

        /// <summary>
        /// Returns a human-readable unlock string.
        /// e.g. "Heat ≥ 100.00 nK"
        /// </summary>
        public override string ToString() => $"{Stage} ≥ {Threshold:0.##} {Unit}";
    }
}
