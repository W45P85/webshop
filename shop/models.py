from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/none.png')
    is_seller = models.BooleanField(default=False)

    def __str__(self):
        if self.user:
            return self.user.username
        else:
            return 'Unbekannter Kunde'

    def get_orders(self):
        return Order.objects.filter(customer=self)

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
    img = models.ImageField(null=True, blank=True, upload_to='product_images/', default='article_pics/none.jpeg')
    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Dispatched', 'dispatched'),
        ('Delivered', 'delivered'),
        ('complained', 'complained'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, db_index=True)
    order_date = models.DateTimeField(auto_now_add=True)
    done = models.BooleanField(default=False, null=True, blank=False)
    order_id = models.CharField(max_length=100, null=True, unique=True, editable=False, default=uuid.uuid4)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, default='Pending')
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipping_provider = models.CharField(max_length=100, blank=True, null=True)

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
    
    def get_ordered_articles(self):
        return self.orderdarticle_set.all()
    
    def address_set(self):
        return self.address_set.all()



class OrderdArticle(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True)
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    order_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        if self.article:
            return self.article.name
        else:
            return 'Unbekannter Artikel'

    @property
    def get_total(self):
        total = self.article.price * self.quantity
        return total


class Address(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True, related_name='addresses')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    address = models.CharField(max_length=200, null=True)
    city = models.CharField(max_length=200, null=True)
    state = models.CharField(max_length=200, null=True, blank=True)
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


class Complaint(models.Model):
    STATUS_CHOICES = [
        ('Received', 'Received'),
        ('In Review', 'In Review'),
        ('Resolved', 'Resolved'),
        ('Rejected', 'Rejected'),
    ]
    
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(default='No reason provided')
    articles = models.ManyToManyField('Article', blank=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Received')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='complaint_images/', null=True, blank=True)

    def __str__(self):
        return f'Reklamation {self.id} - {", ".join(article.name for article in self.articles.all()) if self.articles.exists() else "Unbekannte Artikel"}'