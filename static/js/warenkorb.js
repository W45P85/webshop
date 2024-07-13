let bestellButtons = document.getElementsByClassName('warenkorb-bestellen')

for (let i = 0; i < bestellButtons.length; i++) {
    bestellButtons[i].addEventListener('click', function () {
        let articleId = this.dataset.artikel;
        let action = this.dataset.action;

        if (user == 'AnonymousUser') {
            updateAnonymousOrder(articleId, action);
        } else {
            updateCustomerOrder(articleId, action);
        }
    })
}


function updateAnonymousOrder(articleId, action) {
    //console.log('Gast ' + articleId +  ' ' + action)
    if (action == 'bestellen'){
        if(cart[articleId]  == undefined){
            cart[articleId] = {'quantity': 1}
        } else {
            cart[articleId]['quantity'] += 1
        }
    }
    if (action == 'entfernen'){
        cart[articleId]['quantity'] -= 1

        if(cart[articleId]['quantity'] <= 0){
            delete cart[articleId]
        }
    }
    document.cookie = 'cart=' + JSON.stringify(cart) + ";domain;path=/; SameSite=None; Secure"
    console.log(cart)
    location.reload()
}

function updateCustomerOrder(articleId, action) {
    let url = '/artikel_backend/';

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({'articleId': articleId, 'action': action})
    })
    .then(() => {
        location.reload();
    })
}


// Kasse
let formular = document.getElementById('formular')
let cart_total = document.getElementById('cart_total').value

formular.addEventListener('submit', function (event) {
    event.preventDefault();
    document.getElementById('formular-button').classList.add('d-none');
    document.getElementById('bezahlen-info').classList.remove('d-none');

})

document.getElementById('bezahlen-button').addEventListener('click', function (event) {
    submitFormular();
})

function submitFormular() {
    let customerData = {
        'name': formular.inputName.value,
        'email': formular.inputEmail.value,
        'cart_total': cart_total
    }

    let deliveryAdress = {
        'adress': formular.inputAdress.value,
        'zip': formular.inputPlz.value,
        'city': formular.inputStadt.value,
        'country': formular.inputLand.value
    }
    console.log(customerData, deliveryAdress)

    let url = '/bestellen/';

    fetch (url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({'customerData': customerData, 'deliveryAdress': deliveryAdress})
    })
    .then(() => {
        window.location.href = '/';
    })

}


document.addEventListener('DOMContentLoaded', function() {
    var cartTotalInput = document.getElementById('cart_total');
    if (cartTotalInput) {
        var value = cartTotalInput.value.replace(',', '.'); // Ersetze Komma durch Punkt
        cartTotalInput.value = value; // Setze korrigierten Wert zurück
    }
});

document.addEventListener('DOMContentLoaded', function() {
    let cartTotalInput = document.getElementById('cart_total');
    if (cartTotalInput) {
        let cart_total = cartTotalInput.value;
        // Deine weiteren Aktionen hier
    } else {
        console.error('Element with ID "cart_total" not found.');
    }
});


document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');

    searchInput.addEventListener('input', function() {
        const query = searchInput.value;
        if (query.length > 2) {
            fetch(`/ajax/search/?query=${query}`)
                .then(response => response.json())
                .then(data => {
                    searchResults.innerHTML = '';
                    data.results.forEach(article => {
                        const item = document.createElement('a');
                        item.classList.add('list-group-item', 'list-group-item-action');
                        item.href = `/shop/?query=${article.name}`;
                        item.textContent = article.name;
                        searchResults.appendChild(item);
                    });
                });
        } else {
            searchResults.innerHTML = '';
        }
    });
});