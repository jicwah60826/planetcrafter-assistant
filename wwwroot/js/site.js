// Please see documentation at https://learn.microsoft.com/aspnet/core/client-side/bundling-and-minification
// for details on configuring this project to bundle and minify static web assets.
// v2

function applyFilters() {
    const searchBox = document.getElementById("searchBox");
    const clearBtn  = document.getElementById("searchClear");

    if (!searchBox) return;

    const input = searchBox.value.toLowerCase().trim();
    clearBtn.style.display = input.length > 0 ? "block" : "none";

    document.querySelectorAll('.item-card, .card').forEach(card => {
        const cardName     = (card.dataset.name || '').toLowerCase();
        const matchesSearch = input === '' || cardName.includes(input);
        card.style.display  = matchesSearch ? '' : 'none';
    });
}

function filterCards() {
    applyFilters();
}

function clearSearch() {
    const searchBox = document.getElementById("searchBox");
    searchBox.value = "";
    applyFilters();
    searchBox.focus();
}
