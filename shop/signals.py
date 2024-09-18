from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from .models import Customer, Order
import uuid

User = get_user_model()

@receiver(post_save, sender=User)
def create_customer_and_order_for_superuser(sender, instance, created, **kwargs):
    if created and instance.is_superuser:
        # Erstelle oder hole einen Customer für den Superuser
        customer, customer_created = Customer.objects.get_or_create(user=instance)
        
        if customer_created:
            print(f'Ein neuer Administrator {instance.username} wurde erstellt.')
        
        # Erstelle oder hole die Dummy-Bestellung für den Customer
        order, order_created = Order.objects.get_or_create(customer=customer, done=False)
        
        # Setze die `order_id`, falls sie noch nicht existiert
        if order.order_id is None:
            order.order_id = uuid.uuid4()
            order.save()  # Speichern der Bestellung
        
        if order_created:
            print(f'Eine Dummy-Bestellung wurde für den Administrator {instance.username} erstellt.')
