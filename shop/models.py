from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
from decimal import Decimal


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics', default='profile_pics/none.png')

    def __str__(self):
        if self.user:
            return self.user.username
        else:
            return 'Unbekannter Kunde'

    @property
    def email(self):
        return self.user.email if self.user else ''

    @property
    def first_name(self):
        return self.user.first_name if self.user else ''

    @property
    def last_name(self):
        return self.user.last_name if self.user else ''

class Article(models.Model):
    name = models.CharField(max_length=200, null=True)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    img = models.ImageField(null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    order_date = models.DateTimeField(auto_now_add=True)
    done = models.BooleanField(default=False, null=True, blank=False)
    order_id = models.CharField(max_length=200, null=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id) if self.id is not None else ''
    
    @property
    def get_cart_total(self):
        ordered_articles = self.orderdarticle_set.all()
        cart_total = Decimal('0.00')
        for ordered_article in ordered_articles:
            cart_total += ordered_article.get_total
        return cart_total

    @property
    def get_cart_items(self):
        ordered_articles = self.orderdarticle_set.all()
        cart_items = sum([ordered_article.quantity for ordered_article in ordered_articles])
        return cart_items



class OrderdArticle(models.Model):
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.IntegerField(null=True, blank=True, default=0)
    order_date = models.DateTimeField(default=timezone.now)
    # price = models.FloatField(null=True)

    def __str__(self):
        print(f"Calling __str__ method of {self.__class__.__name__}")
        if self.article:
            return self.article.name
        else:
            return 'Unbekannter Artikel'

    @property
    def get_total(self):
        total = self.article.price * self.quantity
        return total


class Adress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True, related_name='addresses')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    address = models.CharField(max_length=200, null=True)
    city = models.CharField(max_length=200, null=True)
    state = models.CharField(max_length=200, null=True)
    zipcode = models.CharField(max_length=200, null=True)
    country = models.CharField(max_length=200, null=True)
    date = models.DateTimeField(auto_now_add=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.address if self.address else 'Unbekannte Adresse'


class Category(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name