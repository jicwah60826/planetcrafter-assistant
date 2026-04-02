using System.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using PlanetCrafterAssistant.Models;

namespace PlanetCrafterAssistant.Controllers
{
    public class HomeController : Controller
    {
        private readonly ILogger<HomeController> _logger;

        public HomeController(ILogger<HomeController> logger)
        {
            _logger = logger;
        }

        public IActionResult Index()
        {
            return View();
        }

        public IActionResult Privacy()
        {
            return View();
        }

        [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
        public IActionResult Error()
        {
            return View(
                new ErrorViewModel
                {
                    RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier
                }
            );
        }

        public IActionResult Dashboard()
        {
            var resources = new List<Resource>
            {
                new Resource { Name = "Ice", Quantity = 5 },
                new Resource { Name = "Iron", Quantity = 12 }
            };
            return View(resources);
        }

        public IActionResult Details(string id)
        {
            var resource = new Resource { Name = id, Quantity = 10 };
            return View(resource);
        }

        public IActionResult Recipes()
        {
            return View(GetRecipes());
        }

        public IActionResult RecipeDetails(string id)
        {
            var allRecipes = GetRecipes();
            var recipe = allRecipes.FirstOrDefault(r => r.Name == id);
            if (recipe == null)
                return NotFound();
            return View((recipe, allRecipes));
        }

        private List<Recipe> GetRecipes()
        {
            return new List<Recipe>
            {
                // --- Raw ---
                new Recipe
                {
                    Name = "Iron",
                    Category = "Raw",
                    Description = "A basic raw ore found on the planet surface."
                },
                new Recipe
                {
                    Name = "Magnesium",
                    Category = "Raw",
                    Description = "A light metallic raw element."
                },
                new Recipe
                {
                    Name = "Silicon",
                    Category = "Raw",
                    Description = "A raw semiconducting material."
                },
                new Recipe
                {
                    Name = "Cobalt",
                    Category = "Raw",
                    Description = "A raw blue metallic element."
                },
                new Recipe
                {
                    Name = "Titanium",
                    Category = "Raw",
                    Description = "A strong, lightweight raw metal."
                },
                new Recipe
                {
                    Name = "Aluminum",
                    Category = "Raw",
                    Description = "A common lightweight raw metal."
                },
                new Recipe
                {
                    Name = "Iridium",
                    Category = "Raw",
                    Description = "A rare, dense raw metal."
                },
                new Recipe
                {
                    Name = "Uranium",
                    Category = "Raw",
                    Description = "A radioactive raw element."
                },
                new Recipe
                {
                    Name = "Nitrogen",
                    Category = "Raw",
                    Description = "A raw atmospheric gas."
                },
                new Recipe
                {
                    Name = "Obsidian",
                    Category = "Raw",
                    Description = "A raw volcanic glass material."
                },
                new Recipe
                {
                    Name = "Tungsten",
                    Category = "Raw",
                    Description = "A raw metal with a very high melting point."
                },
                // --- Resource ---
                new Recipe
                {
                    Name = "Circuit Board",
                    Category = "Resource",
                    Description = "An electronic component used in advanced crafting.",
                    Ingredients = new List<Ingredient>
                    {
                        new Ingredient { Name = "Silicon", Quantity = 2 },
                        new Ingredient { Name = "Cobalt", Quantity = 1 }
                    }
                },
                new Recipe
                {
                    Name = "Super Alloy",
                    Category = "Resource",
                    Description = "A high-tier material made from a mix of all basic Raws.",
                    Ingredients = new List<Ingredient>
                    {
                        new Ingredient { Name = "Iron", Quantity = 1 },
                        new Ingredient { Name = "Magnesium", Quantity = 1 },
                        new Ingredient { Name = "Silicon", Quantity = 1 },
                        new Ingredient { Name = "Cobalt", Quantity = 1 },
                        new Ingredient { Name = "Titanium", Quantity = 1 },
                        new Ingredient { Name = "Aluminum", Quantity = 1 }
                    }
                },
                new Recipe
                {
                    Name = "Super Alloy Rod",
                    Category = "Resource",
                    Description = "A refined rod crafted from Super Alloy.",
                    Ingredients = new List<Ingredient>
                    {
                        new Ingredient { Name = "Super Alloy", Quantity = 2 }
                    }
                },
                // --- Toxicity ---
                new Recipe
                {
                    Name = "Toxic Goo",
                    Category = "Toxicity",
                    Description = "A hazardous byproduct used in specialized recipes.",
                    Ingredients = new List<Ingredient>
                    {
                        new Ingredient { Name = "Uranium", Quantity = 1 },
                        new Ingredient { Name = "Nitrogen", Quantity = 1 }
                    }
                },
                new Recipe
                {
                    Name = "Pristine Purifying Balm",
                    Category = "Toxicity",
                    Description = "Neutralizes toxicity in the environment.",
                    Ingredients = new List<Ingredient>
                    {
                        new Ingredient { Name = "Toxic Goo", Quantity = 1 },
                        new Ingredient { Name = "Obsidian", Quantity = 2 }
                    }
                },
                // --- Machine ---
                new Recipe
                {
                    Name = "Fusion Generator",
                    Category = "Machine",
                    Description = "Generates power through fusion reactions.",
                    Ingredients = new List<Ingredient>
                    {
                        new Ingredient { Name = "Super Alloy", Quantity = 3 },
                        new Ingredient { Name = "Iridium", Quantity = 2 },
                        new Ingredient { Name = "Circuit Board", Quantity = 2 }
                    }
                }
            };
        }
    }
}
