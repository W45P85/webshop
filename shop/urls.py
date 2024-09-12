from django.urls import path, include
from django.contrib import admin
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.shop, name="shop"),
    
    # Footer
    path('about/', views.about, name='about'),
    path('products/', views.products, name='products'),
    path('awards/', views.awards, name='awards'),
    path('help/', views.help, name='help'),
    path('contact/', views.contact, name='contact'),
    
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
    
    # PDF
    path('generate_pdf/', views.generate_pdf, name='generate_pdf'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),                 # Rechnung durch Button auf pending_orders.html
    path('generate_invoice/<str:order_id>/', views.generate_invoice, name='generate_invoice'),      # Rechnungsdetails
    
    path('generate_delivery-note/<str:order_id>/', views.generate_delivery_note, name='generate_delivery_note'),
    path('delivery_note_detail/<str:delivery_note_id>/', views.delivery_note_detail, name='delivery_note_detail'),
    
    # Rating
    path('ratings/', include('star_ratings.urls', namespace='ratings')),
    
    # payments
    path('paypal/', include("paypal.standard.ipn.urls")),
    path('paypal-ipn/', views.paypal_ipn, name='paypal_ipn'),  # URL für notify_url
    path('payment-success/', views.payment_success, name='payment_success'),  # URL für return_url
    path('payment-cancelled/', views.payment_cancelled, name='payment_cancelled'),  # URL für cancel_return_url
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
    path('order/delete/<uuid:order_id>/', views.delete_order, name='delete_order'),
    path('update_shipping/<uuid:order_id>/', views.update_shipping_status, name='update_shipping_status'),

    # Messages
    path('send/', views.send_message, name='send_message'),
    path('inbox/', views.message_inbox, name='message_inbox'),
    path('message/<int:message_id>/', views.message_detail, name='message_detail'),
    path('message/<int:message_id>/reply/', views.reply_message, name='reply_message'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('chat/<int:recipient_id>/', views.chat_history, name='chat_history'),

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