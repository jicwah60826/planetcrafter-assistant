using Microsoft.AspNetCore.HttpOverrides;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();
builder.Services.AddSingleton<PlanetCrafterAssistant.Services.RecipeService>();

// Expose BUILD_ID to all views via ViewData
var buildId = Environment.GetEnvironmentVariable("BUILD_ID") ?? "dev";
builder.Services.AddSingleton<IHttpContextAccessor, HttpContextAccessor>();
builder.Services.Configure<Microsoft.AspNetCore.Mvc.RazorPages.RazorPagesOptions>(_ => { });

var app = builder.Build();

// Make BUILD_ID available to views via app-level state
app.Use(
    async (ctx, next) =>
    {
        ctx.Items["BuildId"] = buildId;
        await next();
    }
);

// Required when running behind Nginx reverse proxy
app.UseForwardedHeaders(
    new ForwardedHeadersOptions
    {
        ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto
    }
);

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    app.UseHsts();
}

app.UseStaticFiles();
app.UseRouting();
app.UseAuthorization();

app.MapControllerRoute(name: "default", pattern: "{controller=Home}/{action=Recipes}/{id?}");

app.Run();
