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
                new Recipe
                {
                    Name = "Super Alloy",
                    Ingredients = new List<Ingredient>
                    {
                        new Ingredient { Name = "Iron", Quantity = 2 },
                        new Ingredient { Name = "Silicon", Quantity = 1 },
                        new Ingredient { Name = "Aluminum", Quantity = 1 }
                    }
                },
                new Recipe
                {
                    Name = "Rocket Engine",
                    Ingredients = new List<Ingredient>
                    {
                        new Ingredient { Name = "Super Alloy", Quantity = 2 },
                        new Ingredient { Name = "Titanium", Quantity = 3 }
                    }
                }
            };
        }
    }
}
