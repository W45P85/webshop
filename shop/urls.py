from django.urls import path, include
from django.contrib import admin
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.shop, name="shop"),
    
    # Shop
    path("warenkorb/", views.warenkorb, name="warenkorb"),
    path("kasse/", views.kasse, name="kasse"),
    path("artikel_backend/", views.artikelBackend, name="artikel_backend"),
    path('article/<int:id>/', views.article_detail, name='article_detail'),
    path('add_article/', views.add_article, name='add_article'),
    path('add_category/', views.add_category, name='add_category'),
    path('delete_article/<int:article_id>/', views.delete_article_confirmation, name='delete_article_confirmation'),
    path('edit-article/<int:article_id>/', views.edit_article, name='edit_article'),
    
    # Rating
    path('ratings/', include('star_ratings.urls', namespace='ratings')),

    # Authentication
    path("login/", views.loginSeite, name="login"),
    path("logout/", views.logoutUser, name="logout"),
    path("register/", views.regUser, name="register"),
    path("profile/update/", views.update_profile, name='profile_update'),
    
    # Order
    path("bestellen/", views.bestellen, name="bestellen"),
    path("order/<uuid:id>", views.order, name="order"),
    path('pending-orders/', views.pending_orders, name='pending_orders'),

    # Admin
    path('admin/', admin.site.urls, name="django-admin"),
    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Customerdashboard (normal user)
    path("customer_dashboard/", views.customer_dashboard, name="customer_dashboard"),

    # Search
    path("search/", views.search_results, name="search"),
    
    # Legal
    path("imprint/", views.imprint, name="imprint"),
    path("privacy/", views.privacy, name="privacy"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)