from django.contrib import admin
from .models import Customer, Article, Order, OrderdArticle, Address, Category

# Inline admin descriptor for Customer model
class CustomerInline(admin.StackedInline):
    model = Customer
    can_delete = False
    verbose_name_plural = 'Persönliche Angaben'
    fk_name = 'user'

# Define a new User admin
class CustomUserAdmin(admin.ModelAdmin):
    inlines = (CustomerInline, )

# Register Customer model with its admin class
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'email', 'first_name', 'last_name', 'profile_picture']

    def get_queryset(self, request):
        # Exclude customers without a linked user
        return super().get_queryset(request).exclude(user=None)

    def email(self, obj):
        return obj.user.email if obj.user else None

    def first_name(self, obj):
        return obj.user.first_name if obj.user else None

    def last_name(self, obj):
        return obj.user.last_name if obj.user else None

    def profile_picture(self, obj):
        return obj.profile_picture.url if obj.profile_picture else None

    email.admin_order_field = 'user__email'  # Sortieren nach E-Mail
    first_name.admin_order_field = 'user__first_name'  # Sortieren nach Vorname
    last_name.admin_order_field = 'user__last_name'  # Sortieren nach Nachname
    profile_picture.short_description = 'Profilbild'  # Benutzerdefinierte Spaltenüberschrift

# Define Order admin class
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_email', 'order_date', 'done', 'order_id', 'get_cart_total')

    def customer_email(self, obj):
        return obj.customer.user.email if obj.customer and obj.customer.user else "Unknown"

    def order_id(self, obj):
        return obj.order_id

    def get_cart_total(self, obj):
        return obj.get_cart_total

    customer_email.short_description = 'Customer Email'
    order_id.short_description = 'Order ID'
    get_cart_total.short_description = 'Total'

    def changelist_view(self, request, extra_context=None):
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(done=True)

# Define OrderdArticle admin class
@admin.register(OrderdArticle)
class OrderdArticleAdmin(admin.ModelAdmin):
    list_display = ('article_name', 'order_id', 'customer_email', 'quantity', 'order_date')

    def article_name(self, obj):
        return obj.article.name if obj.article else None

    def order_id(self, obj):
        return obj.order.order_id if obj.order else None

    def customer_email(self, obj):
        return obj.order.customer.user.email if obj.order and obj.order.customer and obj.order.customer.user else "Unknown"

    def order_date(self, obj):
        return obj.order.order_date if obj.order else None

    article_name.short_description = 'Artikel Name'  # Benutzerdefinierte Spaltenüberschrift
    order_id.short_description = 'Order ID'  # Benutzerdefinierte Spaltenüberschrift
    customer_email.short_description = 'Kunden E-Mail'  # Benutzerdefinierte Spaltenüberschrift
    order_date.short_description = 'Bestelldatum'  # Benutzerdefinierte Spaltenüberschrift

    def changelist_view(self, request, extra_context=None):
        # Modify changelist view here if needed
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Add any additional filtering or custom queryset logic here
        return qs

# Define Address admin class
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('customer_email', 'order_id', 'address', 'city', 'state', 'zipcode', 'order_date')

    def customer_email(self, obj):
        return obj.customer.user.email if obj.customer and obj.customer.user else "Unknown"

    def order_id(self, obj):
        return obj.order.order_id if obj.order else None

    def order_date(self, obj):
        return obj.order.order_date if obj.order else None

    customer_email.short_description = 'Kunden-E-Mail'  # Benutzerdefinierte Spaltenüberschrift
    order_id.short_description = 'Order ID'  # Benutzerdefinierte Spaltenüberschrift
    order_date.short_description = 'Bestelldatum'  # Benutzerdefinierte Spaltenüberschrift

    def changelist_view(self, request, extra_context=None):
        # Modify changelist view here if needed
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Add any additional filtering or custom queryset logic here
        return qs

# Define Category admin class
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')

    search_fields = ('name',)  # Suche nach Kategorienamen

    def changelist_view(self, request, extra_context=None):
        # Modifiziere die Ansicht der Liste hier nach Bedarf
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Füge zusätzliche Filterung oder benutzerdefinierte Queryset-Logik hier hinzu
        return qs

# Define Article admin class
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price', 'category')

    list_filter = ('category',)  # Filter nach Kategorie

    def changelist_view(self, request, extra_context=None):
        # Modifiziere die Ansicht der Liste hier nach Bedarf
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Füge zusätzliche Filterung oder benutzerdefinierte Queryset-Logik hier hinzu
        return qs
