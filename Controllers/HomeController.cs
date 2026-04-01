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
    }
}
