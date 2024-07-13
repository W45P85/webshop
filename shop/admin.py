from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import *

# Inline admin descriptor for Customer model
class CustomerInline(admin.StackedInline):
    model = Customer
    can_delete = False
    verbose_name_plural = 'Persönliche Angaben'
    fk_name = 'user'

# Define a new User admin
class CustomUserAdmin(UserAdmin):
    inlines = (CustomerInline, )

# Register User with the custom admin class
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register Customer model with its admin class
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'email', 'profile_picture']

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

# Register other models
admin.site.register(Article)
admin.site.register(Order)
admin.site.register(OrderdArticle)
admin.site.register(Adress)
admin.site.register(Category)
