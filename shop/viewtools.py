import json
from . models import *
from django.core.exceptions import ObjectDoesNotExist

def visitorCookieHandler(request):
    try:
        cart = json.loads(request.COOKIES.get('cart', '{}'))
        print(f"Loaded cart from cookies: {cart}")  # Debugging-Ausgabe
    except json.JSONDecodeError:
        cart = {}
        print("Failed to decode cart cookie, initializing empty cart.")  # Debugging-Ausgabe

    articles = []
    order = {'get_cart_total': 0, 'get_cart_items': 0}
    quantity = order['get_cart_items']

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
                    'img': article.img.url if article.img else ''
                },
                'quantity': item_quantity,
                'get_total': cart_total
            }
            articles.append(article_info)
            print(f"Added article {article.name} to cart.")  # Debugging-Ausgabe

        except ObjectDoesNotExist:
            # Handle case where article with this ID does not exist
            print(f"Article with id {article_id} does not exist.")  # Debugging-Ausgabe
            pass

    print(f"Final articles: {articles}")  # Debugging-Ausgabe
    print(f"Final order: {order}")  # Debugging-Ausgabe

    return {'articles': articles, 'order': order}



def visitorOrder(request, data):
    try:
        name = data['customerData']['name']
        email = data['customerData']['email']
        
        cookieData = visitorCookieHandler(request)
        articles = cookieData['articles']
        
        # Find or create customer based on email (for anonymous users)
        customer, created = Customer.objects.get_or_create(user__email=email)
        
        if created:
            customer.name = name
            customer.save()
        
        order = Order.objects.create(customer=customer, done=False)
        
        for article_data in articles:
            article_id = article_data['article']['id']
            quantity = article_data['quantity']
            
            article = Article.objects.get(id=article_id)
            
            OrderdArticle.objects.create(
                order=order,
                article=article,
                quantity=quantity
            )
        
        return customer, order
    
    except Exception as e:
        # Handle any exceptions gracefully and log them
        print(f"Fehler bei der Verarbeitung der Bestellung: {str(e)}")
        return None, None
