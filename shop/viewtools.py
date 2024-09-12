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

        except ObjectDoesNotExist:
            # Handle case where article with this ID does not exist
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
        
        # Create the order
        order = Order.objects.create(customer=customer, done=False)
        
        # Save the address information
        address_data = {
            'address': data['deliveryAddress']['address'],
            'zipcode': data['deliveryAddress']['zip'],
            'city': data['deliveryAddress']['city'],
            'state': data['deliveryAddress']['country'],
            'country': data['deliveryAddress']['country']
        }
        address, created = Address.objects.update_or_create(
            customer=customer, order=order, defaults=address_data
        )
        
        # Save the articles
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


