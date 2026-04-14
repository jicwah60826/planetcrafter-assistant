// Please see documentation at https://learn.microsoft.com/aspnet/core/client-side/bundling-and-minification
// for details on configuring this project to bundle and minify static web assets.
// v2

function applyFilters() {
    const searchBox = document.getElementById("searchBox");
    const clearBtn  = document.getElementById("searchClear");

    if (!searchBox) return;

    const input = searchBox.value.toLowerCase().trim();
    clearBtn.style.display = input.length > 0 ? "block" : "none";

    const activeTab    = document.querySelector('.tab.active');
    const activeFilter = activeTab ? activeTab.dataset.filter : 'all';

    document.querySelectorAll('.item-card, .card').forEach(card => {
        // Use data-name for search — reliable regardless of visibility or layout
        const cardName     = (card.dataset.name || '').toLowerCase();
        const matchesSearch = input === '' || cardName.includes(input);
        const matchesTab    = activeFilter === 'all' || card.dataset.category === activeFilter;
        card.style.display  = matchesSearch && matchesTab ? '' : 'none';
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

document.addEventListener('click', function (e) {
    const tab = e.target.closest('.tab');
    if (!tab) return;

    // Update active state on all sibling tabs
    tab.closest('.filter-tabs')
       .querySelectorAll('.tab')
       .forEach(t => t.classList.remove('active'));

    tab.classList.add('active');
    applyFilters();
});
