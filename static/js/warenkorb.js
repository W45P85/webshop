document.addEventListener('DOMContentLoaded', function () {
    // Initialisierung und Event-Listener für den Warenkorb
    let bestellButtons = document.getElementsByClassName('warenkorb-bestellen');
    console.log('Bestell-Buttons gefunden:', bestellButtons.length);

    for (let i = 0; i < bestellButtons.length; i++) {
        bestellButtons[i].addEventListener('click', function () {
            let articleId = this.dataset.artikel;
            let action = this.dataset.action;

            console.log(`Warenkorb-Aktion: ${action}, Artikel-ID: ${articleId}`);

            if (user === 'AnonymousUser') {
                updateAnonymousOrder(articleId, action);
            } else {
                updateCustomerOrder(articleId, action);
            }
        });
    }

    // Überprüfen der Formular- und cart_total-Elemente
    let formular = document.getElementById('formular');
    let cartTotalInput = document.getElementById('cart_total');

    console.log('Formular gefunden:', formular);
    console.log('Cart Total Input gefunden:', cartTotalInput);

    if (formular && cartTotalInput) {
        let cart_total = parseFloat(cartTotalInput.value.replace(',', '.')) || 0;
        console.log('Initialer Cart Total:', cart_total);

        formular.addEventListener('submit', function (event) {
            event.preventDefault();
            console.log('Formular abgeschickt');

            // Überprüfen, ob PayPal ausgewählt ist
            if (document.getElementById('paypal').checked) {
                console.log('PayPal ausgewählt');
                document.getElementById('bezahlen-info').classList.remove('d-none');
                document.getElementById('formular-button').classList.add('d-none');
            } else {
                console.log('PayPal nicht ausgewählt');
                document.getElementById('bezahlen-info').classList.add('d-none');
                document.getElementById('formular-button').classList.remove('d-none');
            }
        });

        // Event Listener für den PayPal-Button
        let bezahlenButton = document.getElementById('bezahlen-button');
        if (bezahlenButton) {
            bezahlenButton.addEventListener('click', function () {
                console.log('Bezahlen-Button geklickt');
                submitFormular();
            });
        } else {
            console.error('Bezahlen-Button nicht gefunden.');
        }
    } else {
        console.error('Formular oder cart_total Input nicht gefunden.');
    }

    function updateAnonymousOrder(articleId, action) {
        console.log('Update Anonymous Order:', articleId, action);
        if (action === 'bestellen') {
            if (cart[articleId] === undefined) {
                cart[articleId] = { 'quantity': 1 };
            } else {
                cart[articleId]['quantity'] += 1;
            }
        }
        if (action === 'entfernen') {
            if (cart[articleId]) {
                cart[articleId]['quantity'] -= 1;

                if (cart[articleId]['quantity'] <= 0) {
                    delete cart[articleId];
                }
            }
        }
        document.cookie = 'cart=' + JSON.stringify(cart) + ";path=/; SameSite=None; Secure";
        console.log('Aktualisierter Warenkorb:', cart);
        location.reload();
    }

    function updateCustomerOrder(articleId, action) {
        console.log('Update Customer Order:', articleId, action);
        let url = '/artikel_backend/';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({ 'articleId': articleId, 'action': action })
        })
        .then(response => {
            console.log('Antwort erhalten:', response);
            location.reload();
        })
        .catch(error => console.error('Fehler beim UpdateCustomerOrder:', error));
    }

    function submitFormular() {
        if (!formular || !cartTotalInput) {
            console.error('Formular oder cart_total Input nicht gefunden.');
            return;
        }

        let customerData = {
            'name': formular.inputName.value,
            'email': formular.inputEmail.value,
            'cart_total': parseFloat(cartTotalInput.value.replace(',', '.'))
        };

        let deliveryAddress = {
            'address': formular.inputAddress.value,
            'zip': formular.inputZip.value,
            'city': formular.inputCity.value,
            'country': formular.inputCountry.value
        };

        console.log('Kundendaten:', customerData);
        console.log('Lieferadresse:', deliveryAddress);

        let url = '/bestellen/';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({ 'customerData': customerData, 'deliveryAddress': deliveryAddress })
        })
        .then(response => {
            console.log('Antwort erhalten:', response);
            window.location.href = '/';
        })
        .catch(error => console.error('Fehler beim SubmitFormular:', error));
    }

    // Suche-Funktion
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const query = searchInput.value;
            if (query.length > 2) {
                fetch(`/ajax/search/?query=${query}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log('Suchergebnisse:', data.results);
                        searchResults.innerHTML = '';
                        data.results.forEach(article => {
                            const item = document.createElement('a');
                            item.classList.add('list-group-item', 'list-group-item-action');
                            item.href = `/shop/?query=${article.name}`;
                            item.textContent = article.name;
                            searchResults.appendChild(item);
                        });
                    })
                    .catch(error => console.error('Fehler bei der Suche:', error));
            } else {
                searchResults.innerHTML = '';
            }
        });
    }
});
