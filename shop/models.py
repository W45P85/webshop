from django.db import models, transaction
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.utils import timezone
from decimal import Decimal
from PIL import Image
from django.conf import settings
import logging


logger = logging.getLogger(__name__)

def validate_image(image):
    max_size_mb = 5  # Maximale Größe in MB
    if image.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Das Bild darf nicht größer als {max_size_mb} MB sein.")
    
    try:
        img = Image.open(image)
        img_format = img.format.lower()
        allowed_formats = ['jpeg', 'png', 'gif']
        if img_format not in allowed_formats:
            raise ValidationError(f"Nur die Formate {', '.join(allowed_formats)} sind erlaubt.")
    except IOError:
        raise ValidationError("Die Datei ist kein Bild oder ist beschädigt.")


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='customer')
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/none.png')
    is_seller = models.BooleanField(default=False)
    is_registration_complete = models.BooleanField(default=False)

    def __str__(self):
        if self.user:
            return self.user.username
        else:
            return 'Unbekannter Kunde'

    def get_orders(self):
        return Order.objects.filter(customer=self)
    
    def has_addresses(self):
        return self.addresses.exists()

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
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00) # Nettopreis
    img = models.ImageField(null=True, blank=True, upload_to='product_images/', default='article_pics/none.jpeg')
    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True)
    article_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    
    # Dimensions (in appropriate units, e.g., centimeters)
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Units (kilograms)

    # Calculated volume (based on provided units)
    @property
    def volume(self):
        if self.length and self.width and self.height:
            return self.length * self.width * self.height
        else:
            return None  # Handle cases where dimensions are missing

    def __str__(self):
        return self.name


class ShippingMethod(models.Model):
    name = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.cost} €"


class TaxRate(models.Model):
    country = models.CharField(max_length=100)  # ISO 3166-1 Alpha-2 Code
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)  # z.B. 19.00 für 19%

    def __str__(self):
        return f"{self.country}: {self.tax_rate}%"

    @staticmethod
    def get_tax_rate_for_country(country_code):
        logger.debug(f"Looking up tax rate for country code: {country_code}")
        try:
            tax_rate = TaxRate.objects.get(country=country_code)
            logger.debug(f"Found tax rate: {tax_rate.tax_rate} for country code: {country_code}")
            return tax_rate.tax_rate
        except TaxRate.DoesNotExist:
            logger.debug(f"No tax rate found for country code: {country_code}")
            return Decimal('0.00')



class Order(models.Model):
    STATUS_CHOICES = [
        ('----', '----'),
        ('Pending', 'Pending'),
        ('Payed', 'Payed'),
        ('Dispatched', 'Dispatched'),
        ('Delivered', 'Delivered'),
        ('Complained', 'Complained'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, db_index=True)
    order_date = models.DateTimeField(null=True, blank=True)
    done = models.BooleanField(default=False)
    order_id = models.UUIDField(editable=False, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, default='Pending')
    deleted = models.BooleanField(default=False)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipment_status = models.CharField(max_length=50, blank=True, null=True)
    shipping_date = models.DateTimeField(null=True, blank=True)
    shipping_provider = models.CharField(max_length=100, blank=True, null=True)
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.SET_NULL, null=True, blank=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    payed = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return str(self.id) if self.id is not None else ''
    
    def get_cart_total(self):
        ordered_articles = self.orderdarticle_set.all()
        cart_total = Decimal('0.00')
        
        for ordered_article in ordered_articles:
            total = ordered_article.get_total
            cart_total += total
            
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
    
    def get_tax_rate(self):
        try:
            tax_rate = TaxRate.objects.get(country=self.country)
            return tax_rate.tax_rate
        except TaxRate.DoesNotExist:
            return 0.00  # Fallback if no tax rate is found

    def calculate_total(self):
        # Berechnung der Zwischensumme (Artikelkosten)
        subtotal = Decimal(self.get_cart_total())
        
        # Berechnung der Steuer
        tax_rate = Decimal(self.get_tax_rate()) / Decimal('100.00')
        tax_amount = subtotal * tax_rate

        # Berechnung der Versandkosten
        shipping_cost = Decimal(self.shipping_method.cost) if self.shipping_method else Decimal('0.00')

        # Gesamtkosten berechnen: Zwischensumme + Steuern + Versandkosten
        total = subtotal + tax_amount + shipping_cost
        
        # Felder aktualisieren
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.total = total
    
        # Rückgabe der Gesamtkosten
        return total
    
    def save(self, *args, **kwargs):
        try:
            if self.pk is None:
                # Wenn die Instanz neu ist, speichere sie zunächst, um einen Primärschlüssel zu erhalten
                super().save(*args, **kwargs)
                logger.info(f"New order created with ID {self.pk}")
            
            # Berechnung der Gesamtsumme
            self.calculate_total()

            # Speichern der Instanz mit den aktualisierten Feldern
            super().save(update_fields=['subtotal', 'tax_amount', 'total', 'order_id'])
            logger.info(f"Order {self.pk} updated with subtotal: {self.subtotal}, tax_amount: {self.tax_amount}, total: {self.total}, order_id: {self.order_id}")

        except Exception as e:
            logger.error(f"Failed to save order with ID {self.pk}: {str(e)}")
            raise



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
        # Konvertiere den Artikelpreis zu Decimal für die Berechnung
        total = Decimal(self.article.price) * Decimal(self.quantity)
        return total

    def get_tax_rate(self):
        # Verwende den Steuersatz aus der Bestellung als Decimal
        return Decimal(self.order.get_tax_rate())

    @property
    def get_tax_amount(self):
        tax_rate = self.get_tax_rate()
        total_price = self.get_total
        # Berechne die Steuer mit Decimal-Werten
        tax_amount = (total_price * tax_rate) / Decimal('100.00')
        return tax_amount

    @property
    def get_total_incl_tax(self):
        # Berechne den Gesamtpreis inkl. Steuer
        return self.get_total + self.get_tax_amount

    @property
    def get_unit_tax_amount(self):
        # Berechne die Steuer pro Einheit
        tax_rate = self.get_tax_rate()
        unit_price = Decimal(self.article.price)
        unit_tax_amount = (unit_price * tax_rate) / Decimal('100.00')
        return unit_tax_amount



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
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_descendants(self):
        # Gibt alle untergeordneten Kategorien einschließlich der Kinderkategorien zurück
        descendants = []
        def add_children(category):
            children = list(category.children.all())
            for child in children:
                descendants.append(child)
                add_children(child)
        add_children(self)
        return descendants

    @property
    def num_articles(self):
        count = Article.objects.filter(category=self).count()
        for child in self.children.all():
            count += child.num_articles
        return count


class Complaint(models.Model):
    STATUS_CHOICES = [
        ('Received', 'Received'),
        ('In Review', 'In Review'),
        ('Resolved', 'Resolved'),
        ('Rejected', 'Rejected'),
    ]
    
    complaint_id = models.CharField(max_length=50, blank=True, null=True)
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, null=True, blank=True)
    reason = models.TextField(default='No reason provided')
    articles = models.ManyToManyField('Article', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Received')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='complaint_images/', null=True, blank=True)

    def __str__(self):
        return f'Reklamation {self.id} - {", ".join(article.name for article in self.articles.all()) if self.articles.exists() else "Unbekannte Artikel"}'
    
    def save(self, *args, **kwargs):
        if not self.complaint_id:
            self.complaint_id = self.generate_complaint_id()
        super().save(*args, **kwargs)

    def generate_complaint_id(self):
        today = timezone.now()
        date_str = today.strftime("%Y-%m-%d")  # Formatierung als YYYY-MM-DD für URL-Kompatibilität
        last_complaint = Complaint.objects.filter(created_at__date=today.date()).order_by('-created_at').first()
        if last_complaint and last_complaint.complaint_id:
            # Extrahiere die letzte Nummer aus der complaint_id
            try:
                last_number = int(last_complaint.complaint_id.split('-')[-1].lstrip('0') or '0')
            except ValueError:
                last_number = 0
            new_number = last_number + 1
        else:
            new_number = 1
        return f"{date_str}-R-{new_number:04d}"


def invoice_upload_to(instance, filename):
    customer_username = instance.order.customer.user.username if instance.order.customer.user else 'anonymous'
    return f'invoices/{customer_username}/{filename}'
class Invoice(models.Model):
    invoice_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    pdf = models.FileField(upload_to=invoice_upload_to, null=True, blank=True)  # Falls redundant, entferne `upload_to=invoice_upload_to`
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rechnung {self.id} für Bestellung {self.order.order_id}"

    @staticmethod
    def get_next_invoice_id():
        last_invoice = Invoice.objects.all().order_by('-id').first()
        last_number = last_invoice.id if last_invoice else 0
        next_number = last_number + 1
        return f'R-{next_number}'


def delivery_note_upload_to(instance, filename):
    customer_username = instance.order.customer.user.username if instance.order.customer.user else 'anonymous'
    return f'delivery_notes/{customer_username}/{filename}'
class DeliveryNote(models.Model):
    delivery_note_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    pdf = models.FileField(upload_to=delivery_note_upload_to, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Lieferschein {self.id} für Bestellung {self.order.order_id}"

    @staticmethod
    def get_next_delivery_note_id():
        last_note = DeliveryNote.objects.all().order_by('-id').first()
        last_number = last_note.id if last_note else 0
        next_number = last_number + 1
        return f'L-{next_number}'


class Message(models.Model):
    '''
    sender: Der Benutzer, der die Nachricht sendet.
    recipient: Der Benutzer, der die Nachricht empfängt.
    subject: Der Betreff der Nachricht.
    body: Der Inhalt der Nachricht.
    sent_at: Der Zeitpunkt, zu dem die Nachricht gesendet wurde.
    read_at: Der Zeitpunkt, zu dem die Nachricht gelesen wurde (optional).
    '''
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"From {self.sender.username} to {self.recipient.username} - {self.subject}"

    def mark_as_read(self):
        self.read_at = timezone.now()
        self.save()
