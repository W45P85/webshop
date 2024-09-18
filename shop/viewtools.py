import json
from . models import *
from django.core.exceptions import ObjectDoesNotExist

def visitorCookieHandler(request):
    try:
        cart = json.loads(request.COOKIES.get('cart', '{}'))
    except json.JSONDecodeError:
        cart = {}
    
    articles = []
    order = {'get_cart_total': 0, 'get_cart_items': 0}

    for article_id, item_data in cart.items():
        try:
            article = Article.objects.get(id=int(article_id))
            item_quantity = item_data.get('quantity', 0)
            cart_total = article.price * item_quantity

            order['get_cart_total'] += cart_total
            order['get_cart_items'] += item_quantity

            article_info = {
                'article': {
                    'id': article.id,
                    'name': article.name,
                    'price': article.price,
                    'img': article.img.url if article.img else ''  # Sicherstellen, dass img existiert
                },
                'quantity': item_quantity,
                'get_total': cart_total
            }
            articles.append(article_info)

        except ObjectDoesNotExist:
            # Logge oder drucke die fehlenden Artikel-IDs, falls gewünscht
            print(f"Artikel mit ID {article_id} existiert nicht.")
            pass

    return {'articles': articles, 'order': order}



def visitorOrder(request, data):
    try:
        name = data['customerData']['name']
        email = data['customerData']['email']
        
        cookieData = visitorCookieHandler(request)
        articles = cookieData['articles']
        
        # Find or create user based on email (for anonymous users)
        user, user_created = User.objects.get_or_create(email=email, defaults={'username': email})
        
        if user_created:
            user.set_unusable_password()  # Set a non-usable password for anonymous users
        
        # Set user's name
        if ' ' in name:
            first_name, last_name = name.split(' ', 1)
        else:
            first_name = name
            last_name = ''
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        # Find or create customer based on user
        customer, customer_created = Customer.objects.get_or_create(user=user)
        
        # Find or create the order with status '----'
        order, created = Order.objects.get_or_create(customer=customer, status='----')
        
        if created:
            print("Neue Bestellung erstellt:", order)
        
        # Save the address information
        address_data = {
            'address': data['deliveryAddress']['address'],
            'zipcode': data['deliveryAddress']['zip'],
            'city': data['deliveryAddress']['city'],
            'state': data['deliveryAddress']['country'],
            'country': data['deliveryAddress']['country']
        }
        address, address_created = Address.objects.update_or_create(
            customer=customer, order=order, defaults=address_data
        )
        if not address_created:
            print("Adresse aktualisiert:", address)
        else:
            print("Adresse erstellt:", address)
        
        # Save the articles
        for article_data in articles:
            article_id = article_data['article']['id']
            quantity = article_data['quantity']
            
            try:
                article = Article.objects.get(id=article_id)
                # Aktualisieren oder Erstellen der OrderdArticle-Einträge
                OrderdArticle.objects.update_or_create(
                    order=order,
                    article=article,
                    defaults={'quantity': quantity}
                )
            except ObjectDoesNotExist:
                print(f"Artikel mit ID {article_id} nicht gefunden.")
        
        return customer, order
    
    except Exception as e:
        # Handle any exceptions gracefully and log them
        print(f"Fehler bei der Verarbeitung der Bestellung: {str(e)}")
        return None, None



