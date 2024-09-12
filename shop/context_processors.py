from . models import Order, Customer, Message
import json

def cart_count(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, done=False)

        if order:
            quantity = order.get_cart_items
        else:
            quantity = 0
    else:
        quantity = 0
        try:
            cart = json.loads(request.COOKIES['cart'])
        except:
            cart = {}
        for i in cart:
            quantity += cart[i]['quantity']

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