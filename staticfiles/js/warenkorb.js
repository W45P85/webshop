document.addEventListener('DOMContentLoaded', function () {
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
            location.reload();
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
