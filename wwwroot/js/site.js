// Please see documentation at https://learn.microsoft.com/aspnet/core/client-side/bundling-and-minification
// for details on configuring this project to bundle and minify static web assets.

    function filterCards() {
        let input = document.getElementById("searchBox").value.toLowerCase();
    let cards = document.getElementsByClassName("card");

    for (let i = 0; i < cards.length; i++) {
        let text = cards[i].innerText.toLowerCase();
    cards[i].style.display = text.includes(input) ? "" : "none";
        }
    }
