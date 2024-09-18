document.addEventListener('DOMContentLoaded', function () {
    var csrftoken = '{{ csrf_token }}';
    
    // Initialisierung und Event-Listener für den Warenkorb
    let bestellButtons = document.getElementsByClassName('warenkorb-bestellen');
    for (let i = 0; i < bestellButtons.length; i++) {
        bestellButtons[i].addEventListener('click', function () {
            let articleId = this.dataset.artikel;
            let action = this.dataset.action;
            if (user === 'AnonymousUser') {
                updateAnonymousOrder(articleId, action);
            } else {
                updateCustomerOrder(articleId, action);
            }
        });
    }

    let formular = document.getElementById('formular');
    let cartTotalInput = document.getElementById('cart_total');

    if (formular && cartTotalInput) {
        formular.addEventListener('submit', function (event) {
            event.preventDefault();
            if (!formular.checkValidity()) {
                event.stopPropagation();
                formular.classList.add('was-validated');
                return;
            }
            // Überprüfen, ob PayPal ausgewählt ist
            if (document.getElementById('paypal').checked) {
                document.getElementById('bezahlen-info').classList.remove('d-none');
                document.getElementById('formular-button').classList.add('d-none');
            } else {
                document.getElementById('bezahlen-info').classList.add('d-none');
                document.getElementById('formular-button').classList.remove('d-none');
            }
        });

        let bezahlenButton = document.getElementById('bezahlen-button');
        if (bezahlenButton) {
            bezahlenButton.addEventListener('click', function () {
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
    
        // Initialisiere `cart`, falls es noch nicht existiert
        if (!window.cart) {
            window.cart = {};
        }
    
        if (action === 'bestellen') {
            if (window.cart[articleId] === undefined) {
                window.cart[articleId] = { 'quantity': 1 };
            } else {
                window.cart[articleId]['quantity'] += 1;
            }
        }
        if (action === 'entfernen') {
            if (window.cart[articleId]) {
                window.cart[articleId]['quantity'] -= 1;
    
                if (window.cart[articleId]['quantity'] <= 0) {
                    delete window.cart[articleId];
                }
            }
        }
    
        let cookieString = 'cart=' + JSON.stringify(window.cart) + ";path=/";
        if (location.protocol === 'https:') {
            cookieString += "; SameSite=None; Secure";
        }
        document.cookie = cookieString;
    
        console.log('Aktualisierter Warenkorb:', window.cart);
        location.reload();
    }
    

    function updateCustomerOrder(articleId, action) {
        console.log('updateCustomerOrder triggered:', articleId, action);
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
            if (!response.ok) {
                throw new Error('Netzwerkantwort war nicht ok');
            }
            return response.json(); // Oder response.text(), je nachdem, was du zurückgibst
        })
        .then(data => {
            console.log('Erfolgreiche Antwort:', data);
            location.reload(); // Oder eine andere Verarbeitung
        })
        .catch(error => console.error('Fehler beim UpdateCustomerOrder:', error));
    }

    function submitFormular() {
        if (!formular || !cartTotalInput) {
            console.error('Formular oder cart_total Input nicht gefunden.');
            return;
        }

        if (!formular.checkValidity()) {
            console.error('Formular ist nicht gültig.');
            formular.classList.add('was-validated');
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
            window.location.href = '/';
        })
        .catch(error => console.error('Fehler beim SubmitFormular:', error));
    }
});
