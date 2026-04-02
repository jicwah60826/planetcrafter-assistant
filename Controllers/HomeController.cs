using System.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using PlanetCrafterAssistant.Models;
using PlanetCrafterAssistant.Services;

namespace PlanetCrafterAssistant.Controllers
{
    public class HomeController : Controller
    {
        private readonly ILogger<HomeController> _logger;
        private readonly IWebHostEnvironment _env;
        private readonly RecipeService _recipeService;

        public HomeController(
            ILogger<HomeController> logger,
            IWebHostEnvironment env,
            RecipeService recipeService
        )
        {
            _logger = logger;
            _env = env;
            _recipeService = recipeService;
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
            var recipes = _recipeService.GetAll();

            var iconsPath = Path.Combine(_env.WebRootPath, "icons");
            var availableIcons = Directory.Exists(iconsPath)
                ? Directory
                    .GetFiles(iconsPath, "*.png")
                    .Select(f => Path.GetFileNameWithoutExtension(f))
                    .ToHashSet(StringComparer.OrdinalIgnoreCase)
                : new HashSet<string>();

            ViewBag.AvailableIcons = availableIcons;
            return View(recipes);
        }

        public IActionResult RecipeDetails(string id)
        {
            var allRecipes = _recipeService.GetAll();
            var recipe = allRecipes.FirstOrDefault(r => r.Name == id);
            if (recipe == null)
                return NotFound();
            return View((recipe, allRecipes));
        }
    }
}
