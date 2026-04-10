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
    /// Base unlock condition. Use the <c>type</c> discriminator field to determine
    /// which subclass properties apply.
    /// Supported types: "terraformation", "blueprint", "trade", "always", "story"
    /// </summary>
    public class UnlockCondition
    {
        /// <summary>
        /// Discriminator. One of: "terraformation", "blueprint", "trade", "always", "story"
        /// </summary>
        public string Type { get; set; } = "terraformation";

        // ── Terraformation fields ──────────────────────────────────────────────
        /// <summary>
        /// The terraforming index that must be reached.
        /// e.g. "Heat", "Pressure", "Oxygen", "Biomass", "Plants", "Insects", "Animals"
        /// Only used when Type = "terraformation".
        /// </summary>
        public string? Stage { get; set; }

        /// <summary>
        /// The numeric value that must be reached.
        /// Only used when Type = "terraformation".
        /// </summary>
        public double? Threshold { get; set; }

        /// <summary>
        /// The display unit for the threshold value. e.g. "nK", "µPa", "ppm", "g"
        /// Only used when Type = "terraformation".
        /// </summary>
        public string? Unit { get; set; }

        // ── Blueprint fields ───────────────────────────────────────────────────
        /// <summary>
        /// Optional label for where the chip is found or obtained.
        /// e.g. "Crashed Ship — Sector 7", "Wrecked Rover — North Cave"
        /// Only used when Type = "blueprint".
        /// </summary>
        public string? BlueprintSource { get; set; }

        // ── Trade Platform fields ──────────────────────────────────────────────
        /// <summary>
        /// The trade cost to unlock via the Trade Platform, if applicable.
        /// Only used when Type = "trade".
        /// </summary>
        public string? TradeCost { get; set; }

        // ── Story fields ───────────────────────────────────────────────────────
        /// <summary>
        /// A short label describing the story event that grants the unlock.
        /// Only used when Type = "story".
        /// </summary>
        public string? StoryEvent { get; set; }

        public override string ToString() =>
            Type switch
            {
                "terraformation" => $"{Stage} ≥ {Threshold:0.##} {Unit}",
                "blueprint"
                    => BlueprintSource != null
                        ? $"Blueprint Chip ({BlueprintSource})"
                        : "Blueprint Chip",
                "trade" => TradeCost != null ? $"Trade Platform — {TradeCost}" : "Trade Platform",
                "story" => StoryEvent != null ? $"Story: {StoryEvent}" : "Story Progression",
                "always" => "Available from the start",
                _ => "Unknown"
            };
    }
}
