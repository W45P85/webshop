from . models import Order, Customer, Message
import json

def cart_count(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        # Filter für offene Bestellungen
        orders = Order.objects.filter(customer=customer, status='----')
        
        if orders.exists():
            order = orders.first()  # Nimm die erste Bestellung, wenn mehrere vorhanden sind
            quantity = order.get_cart_items  # Berechne die Menge der Artikel in dieser Bestellung
        else:
            quantity = 0
    else:
        quantity = 0
        try:
            cart = json.loads(request.COOKIES.get('cart', '{}'))
        except json.JSONDecodeError:
            cart = {}
        
        # Berechne die Menge der Artikel im Cookie-Warenkorb
        for i in cart:
            quantity += cart[i].get('quantity', 0)

    return {'quantity': quantity}



def customer_profile(request):
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            customer = None
    else:
        customer = None

    return {
        'customer': customer
    }


def unread_messages_count(request):
    if request.user.is_authenticated:
        unread_count = Message.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
    else:
        unread_count = 0

    return {'unread_messages_count': unread_count}