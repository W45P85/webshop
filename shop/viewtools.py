import json
from . models import *

def visitorCookieHandler(request):
    try:
        cart = json.loads(request.COOKIES['cart'])
    except:
        cart = {}

    articles = []
    order = {'get_cart_total': 0, 'get_cart_items': 0}
    quantity = order['get_cart_items']

    for i in cart:
        quantity += cart[i]['quantity']
        article = Article.objects.get(id=i)
        cart_total = (article.price * cart[i]['quantity'])
        order['get_cart_total'] += cart_total
        order['get_cart_items'] += cart[i]['quantity']

        article = {
            'article': {
                'id': article.id,
                'name': article.name,
                'price': article.price,
                'img': article.img
            },
            'quantity': cart[i]['quantity'],
            'get_total': cart_total
        }
        articles.append(article)
        
    return {'articles': articles, 'order': order}


def visitorOrder(request, data):
    name = data['customerData']['name']
    email = data['customerData']['email']
    
    cookieData = visitorCookieHandler(request)
    articles = cookieData['articles']
    
    customer, created = Customer.objects.get_or_create(email=email)
    customer.name = name
    customer.save()
    
    order = Order.objects.create(customer=customer, done=False)
    for i in articles:
        article = Article.objects.get(id=i['article']['id'])
        orderdarticle = OrderdArticle.objects.create(
            order=order,
            article=article,
            quantity=i['quantity']
        )
    return customer, order