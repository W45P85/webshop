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
    path('category/<int:pk>/', views.category_detail, name='category_detail'),
    path('delete_article/<int:article_id>/', views.delete_article_confirmation, name='delete_article_confirmation'),
    path('edit-article/<int:article_id>/', views.edit_article, name='edit_article'),
    path('customer_complaints/', views.customer_complaints, name='customer_complaints'),
    path('search-order/', views.search_order, name='search_order'),
    path('complaint-form/<uuid:order_id>/', views.complaint_form, name='complaint_form'),
    path('mark-delivered/', views.mark_delivered, name='mark_delivered'),
    
    # Rating
    path('ratings/', include('star_ratings.urls', namespace='ratings')),
    
    # payments
    # path('payment/', views.bestellen, name='payment'),

    # Authentication
    path("login/", views.loginSeite, name="login"),
    path("logout/", views.logoutUser, name="logout"),
    path("register/", views.regUser, name="register"),
    path("profile/update/", views.update_profile, name='profile_update'),
    
    # Order
    path("bestellen/", views.bestellen, name="bestellen"),
    path("order/<uuid:id>", views.order, name="order"),
    path('pending-orders/', views.pending_orders, name='pending_orders'),
    path('complaint/<str:complaint_id>/', views.complaint_detail, name='complaint_detail'),

    # Admin
    path('admin/', admin.site.urls, name="django-admin"),
    
    # Seller
    path("seller_dashboard/", views.seller_dashboard, name="seller_dashboard"),

    # Customerdashboard (normal user)
    path("customer_dashboard/", views.customer_dashboard, name="customer_dashboard"),

    # Search
    path("search/", views.search_results, name="search"),
    
    # Legal
    path("imprint/", views.imprint, name="imprint"),
    path("privacy/", views.privacy, name="privacy"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)