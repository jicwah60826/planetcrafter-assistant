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
        private readonly TipsService _tipsService;

        public HomeController(
            ILogger<HomeController> logger,
            IWebHostEnvironment env,
            RecipeService recipeService,
            TipsService tipsService
        )
        {
            _logger = logger;
            _env = env;
            _recipeService = recipeService;
            _tipsService = tipsService;
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

            var categories = recipes
                .Select(r => r.Category)
                .Where(c => !string.IsNullOrWhiteSpace(c))
                .Distinct()
                .OrderBy(c => c)
                .ToList();

            ViewBag.Categories = categories;
            ViewData["ShowHomeIcon"] = true;
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

        public IActionResult About()
        {
            return View();
        }

        public IActionResult TipsAndTricks()
        {
            var tips = _tipsService.GetAll();
            ViewData["ShowHomeIcon"] = true;
            return View(tips);
        }
    }
}
