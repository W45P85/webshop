from django.db import models
from django.contrib.auth.models import User


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics', default='profile_pics/none.png')
    
    def __str__(self):
        return self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

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

    def __str__(self):
        return str(self.id)
    
    @property
    def get_cart_total(self):
        orderd_articles = self.orderdarticle_set.all()
        cart_total = sum([orderd_article.get_total for orderd_article in orderd_articles])
        return cart_total
    
    @property
    def get_cart_items(self):
        orderd_articles = self.orderdarticle_set.all()
        cart_items = sum([orderd_article.quantity for orderd_article in orderd_articles])
        return cart_items

class OrderdArticle(models.Model):
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.IntegerField(null=True, blank=True, default=0)
    order_date = models.DateTimeField(auto_now_add=True)
    # price = models.FloatField(null=True)

    def __str__(self):
        return self.article.name

    @property
    def get_total(self):
        total = self.article.price * self.quantity
        return total

class Adress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    address = models.CharField(max_length=200, null=True)
    city = models.CharField(max_length=200, null=True)
    state = models.CharField(max_length=200, null=True)
    zipcode = models.CharField(max_length=200, null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.address


class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name