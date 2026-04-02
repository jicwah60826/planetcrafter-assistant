// Please see documentation at https://learn.microsoft.com/aspnet/core/client-side/bundling-and-minification
// for details on configuring this project to bundle and minify static web assets.

    function filterCards() {
    const input = document.getElementById("searchBox").value.toLowerCase();
    document.querySelectorAll('.item-card, .card').forEach(card => {
        card.style.display = card.innerText.toLowerCase().includes(input) ? '' : 'none';
    });
}
