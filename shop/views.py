import json
import os
import uuid
import logging
import base64
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.dispatch import receiver
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, FloatField, ExpressionWrapper
from datetime import timedelta
from . forms import CustomerCreationForm, SearchForm, AddArticleForm, AddCategoryForm, EditArticleForm, ProfileForm, TrackingNumberForm, ComplaintForm, OrderSearchForm, MarkDeliveredForm, ShippingForm, MessageForm, MessageReplyForm
from . models import *
from . viewtools import visitorCookieHandler, visitorOrder
from django.http import HttpResponseNotFound, JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from paypal.standard.forms import PayPalPaymentsForm
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from urllib.parse import unquote
from django.db.models.signals import pre_save
from xhtml2pdf import pisa
from io import BytesIO
from django.template.loader import render_to_string, get_template
from .dhl_utils import send_package_with_dhl
from django.views.decorators.csrf import csrf_exempt
from paypal.standard.models import ST_PP_COMPLETED, ST_PP_PENDING


logger = logging.getLogger(__name__)

def is_admin_or_seller(user):
    return user.groups.filter(name='Admins').exists() or user.groups.filter(name='Sellers').exists()

def about(request):
    return render(request, 'shop/basic/about.html')
def products(request):
    return render(request, 'shop/basic/products.html')
def awards(request):
    return render(request, 'shop/basic/awards.html')
def help(request):
    return render(request, 'shop/basic/help.html')
def contact(request):
    return render(request, 'shop/basic/contact.html')


def shop(request):
    # Holen aller Kategorien
    categories = Category.objects.all().order_by('name')
    articles = Article.objects.all()

    category_filter = request.GET.get('category')
    if category_filter:
        articles = Article.objects.filter(category__name=category_filter)
    else:
        articles = Article.objects.all()

    # Separieren der Hauptkategorien von den Kindkategorien
    top_level_categories = categories.filter(parent__isnull=True)

    ctx = {
        'top_level_categories': top_level_categories,
        'articles': articles,
    }

    return render(request, 'shop/shop.html', ctx)


def is_cookie_accepted(request, cookie_name):
    cookie_consent = request.COOKIES.get('cookiebanner', '')
    if not cookie_consent:
        print("Cookie not accepted")
        return False
    
    # Decode the URL-encoded cookie value
    decoded_consent = unquote(cookie_consent)
    accepted_cookies = decoded_consent.split(',')
    return cookie_name in accepted_cookies


def warenkorb(request):
    order = None
    articles = []

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, done=False)
        articles = order.orderdarticle_set.all()
    else:
        essential_accepted = is_cookie_accepted(request, 'essential')

        if essential_accepted:
            cookieData = visitorCookieHandler(request)
            articles = cookieData.get('articles', [])
            order = cookieData.get('order', None)
        else:
            articles = []
            order = {'get_cart_total': 0, 'get_cart_items': 0}

    ctx = {
        'articles': articles,
        'order': order,
    }

    return render(request, 'shop/warenkorb.html', ctx)


def kasse(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, done=False)
        articles = order.orderdarticle_set.all()
        
        # Versuche, die Standardadresse des Kunden zu finden
        address = customer.addresses.filter(is_default=True).first()
        
        # Wenn keine Standardadresse gefunden wird, nehme die letzte gespeicherte Adresse
        if not address:
            address = customer.addresses.order_by('-date').first()

        if address:
            logging.debug(f"Adresse gefunden: {address.address}, {address.city}, {address.zipcode}, {address.country}")
        else:
            logging.debug("Keine Adresse gefunden")
    else:
        if is_cookie_accepted(request, 'essential'):
            cookiedata = visitorCookieHandler(request)
            articles = cookiedata['articles']
            order = cookiedata['order']
        else:
            articles = []
            order = None
        address = None

    ctx = {
        'articles': articles,
        'order': order,
        'address': address,
    }
    return render(request, 'shop/kasse.html', ctx)


def artikelBackend(request):
    data = json.loads(request.body)
    articleId = data['articleId']
    action = data['action']
    customer = request.user.customer
    article = Article.objects.get(id=articleId)
    order, created = Order.objects.get_or_create(customer=customer, done=False)
    ordered_article, created = OrderdArticle.objects.get_or_create(order=order, article=article)

    if action == 'bestellen':
        ordered_article.quantity = (ordered_article.quantity + 1)
        messages.success(request, 'Artikel wurde zum Warenkorb hinzugefügt.')
    elif action == 'entfernen':
        ordered_article.quantity = (ordered_article.quantity - 1)
        messages.warning(request, 'Artikel wurde aus dem Warenkorb entfernt.')

    ordered_article.save()

    if ordered_article.quantity <= 0:
        ordered_article.delete()

    return JsonResponse("Artikel hinzugefügt", safe=False)


def loginSeite(request):
    page = 'login'
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Benutzerrollen prüfen
            user_groups = user.groups.values_list('name', flat=True)
            if 'Admins' in user_groups or 'Sellers' in user_groups:
                return redirect('seller_dashboard')
            else:
                return redirect('shop')
        else:
            messages.error(request, 'Benutzername oder Passwort ungültig.')

    return render(request, 'shop/login.html', {'page': page})


def logoutUser(request):
    if request.user.is_authenticated:
    
        logout(request)
    return redirect('shop')


def regUser(request):
    page = 'reg'
    if request.method == 'POST':
        user_form = CustomerCreationForm(request.POST)
        profile_form = ProfileForm(request.POST, request.FILES)
        
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile_form.save(user=user)

            login(request, user)
            messages.success(request, f'Benutzer {user.username} wurde erfolgreich erstellt.')
            return redirect('shop')
        else:
            # Log errors for debugging
            user_form_errors = user_form.errors.as_data()
            profile_form_errors = profile_form.errors.as_data()
            
            # Print errors to console
            print('User Form Errors:', user_form_errors)
            print('Profile Form Errors:', profile_form_errors)
            
            # Add errors to messages
            for field, errors in user_form_errors.items():
                for error in errors:
                    messages.error(request, f'Fehler im Benutzerformular ({field}): {error}')
            for field, errors in profile_form_errors.items():
                for error in errors:
                    messages.error(request, f'Fehler im Profilformular ({field}): {error}')
    else:
        user_form = CustomerCreationForm()
        profile_form = ProfileForm()

    ctx = {'user_form': user_form, 'profile_form': profile_form, 'page': page}
    return render(request, 'shop/registration_form.html', ctx)


@login_required
def update_profile(request):
    user = request.user
    customer = user.customer
    
    # Adressfindungslogik
    address = customer.addresses.filter(is_default=True).first()
    if not address:
        address = customer.addresses.order_by('-date').first()

    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, request.FILES, instance=customer)
        password_form = PasswordChangeForm(user, request.POST)
        
        if profile_form.is_valid() and password_form.is_valid():
            profile_form.save(user)
            password_form.save()
            messages.success(request, 'Profil wurde erfolgreich aktualisiert.')
            return redirect('profile_update')
        else:
            messages.error(request, 'Bitte korrigieren Sie die Fehler im Formular.')
    else:
        profile_form = ProfileForm(instance=customer, initial={
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'address': address.address if address else '',
            'city': address.city if address else '',
            'state': address.state if address else '',
            'zipcode': address.zipcode if address else '',
            'country': address.country if address else '',
            'is_default': address.is_default if address else False,
        })
        password_form = PasswordChangeForm(user)
    
    ctx = {
        'profile_form': profile_form,
        'password_form': password_form
    }
    
    return render(request, 'shop/profile_update.html', ctx)


def check_and_fix_customers():
    customers = Customer.objects.all()
    for customer in customers:
        if customer.user is None:
            # Code einfügen, um das Problem zu beheben
            # Zum Beispiel: Einen neuen Benutzer erstellen und mit dem Kunden verknüpfen
            # user = User.objects.create(username='neuer_benutzername', email='...')
            # customer.user = user
            # customer.save()
            print(f"Customer {customer.id} hat keine zugeordnete User-Instanz.")


def bestellen(request):
    try:
        logging.info("Starting bestellen view")
        
        # Default URLs (Umgebungsvariablen können später genutzt werden, nachdem 'order' definiert ist)
        notify_url = os.environ.get('PAYPAL_NOTIFY_URL')
        cancel_return_url = os.environ.get('PAYPAL_CANCEL_RETURN_URL')
        
        data = json.loads(request.body)
        logging.info(f"Received data: {data}")

        # Default cart_total value
        cart_total = 0.00

        # Validation of required fields in customerData and deliveryAddress
        required_customer_fields = ['name', 'email']
        required_address_fields = ['address', 'zip', 'city', 'country']
        
        for field in required_customer_fields:
            if field not in data['customerData'] or not data['customerData'][field]:
                logging.error(f"Missing or empty field in customerData: {field}")
                return HttpResponseBadRequest(f"Field '{field}' is required.")
        
        for field in required_address_fields:
            if field not in data['deliveryAddress'] or not data['deliveryAddress'][field]:
                logging.error(f"Missing or empty field in deliveryAddress: {field}")
                return HttpResponseBadRequest(f"Field '{field}' is required.")

        if request.user.is_authenticated:
            customer = request.user.customer
            order = Order.objects.filter(customer=customer, done=False).first()
            if order is None:
                order = Order.objects.create(customer=customer, done=False)

            address_data = {
                'address': data['deliveryAddress']['address'],
                'zipcode': data['deliveryAddress']['zip'],
                'city': data['deliveryAddress']['city'],
                'state': data['deliveryAddress']['country'],
                'country': data['deliveryAddress']['country']
            }
            address, created = Address.objects.update_or_create(
                customer=customer, order=order, defaults=address_data
            )

        else:
            customer, order = visitorOrder(request, data)
            if customer is None or order is None:
                return HttpResponse('Fehler bei der Bestellung für anonymen Benutzer.')

        cart_total_data = data['customerData'].get('cart_total', '0.00')
        
        if isinstance(cart_total_data, str):
            cart_total_data = cart_total_data.replace(',', '.')
            cart_total = float(cart_total_data)
        elif isinstance(cart_total_data, (int, float)):
            cart_total = float(cart_total_data)
        else:
            return HttpResponseBadRequest("Invalid cart total format")

        # Set the order ID before saving
        order.order_id = uuid.uuid4()
        order.order_date = timezone.now()
        order.save()

        # Jetzt kann auf order.order_id zugegriffen werden
        return_url = f"{os.environ.get('PAYPAL_RETURN_URL')}?order_id={order.order_id}"

        logging.info(f"Notify URL: {notify_url}")
        logging.info(f"Return URL: {return_url}")
        logging.info(f"Cancel Return URL: {cancel_return_url}")
        
        paypal_dict = {
            "business": os.environ.get('PAYPAL_BUSINESS'),
            "amount": format(order.get_cart_total(), '.2f'),
            "invoice": order.order_id,
            "currency_code": os.environ.get('PAYPAL_CURRENCY'),
            "notify_url": notify_url,
            "return": return_url,
            "cancel_return": cancel_return_url,
        }

        paypal_form = PayPalPaymentsForm(initial=paypal_dict)
        order_url = str(order.order_id)
        messages.success(request, mark_safe(
            f"Vielen Dank für Ihre Bestellung: <a href='/order/{order_url}'>{order_url}</a>"
            "<br>Jetzt mit PayPal bezahlen:"
            f"<br>{paypal_form.render()}"
        ))

        response = HttpResponse('Bestellung erfolgreich')
        response.delete_cookie('cart')

        return response
    
    except Exception as e:
        logging.error(f"Error in bestellen view: {str(e)}")
        return HttpResponseServerError("Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.")




@csrf_exempt
def paypal_ipn(request):
    logger.info("Starting PayPal IPN processing.")
    if request.method == "POST":
        # PayPal sendet IPN-Daten an diese URL
        try:
            ipn_obj = request.POST

            order_id = ipn_obj.get('invoice')
            payment_status = ipn_obj.get('payment_status')
            txn_id = ipn_obj.get('txn_id')

            logger.info(f"Received IPN for order ID: {order_id} with payment status: {payment_status} and transaction ID: {txn_id}")

            try:
                order = Order.objects.get(order_id=order_id)
            except Order.DoesNotExist:
                logger.error(f"Order with ID {order_id} not found.")
                return HttpResponse("Order not found", status=404)

            # Überprüfen, ob die Zahlung erfolgreich war
            if payment_status == ST_PP_COMPLETED:
                # Zahlung erfolgreich, Bestellung als abgeschlossen und bezahlt markieren
                order.done = True
                order.paid = True
                order.payment_status = 'Payed'
                order.status = 'Payed'
                order.payment_id = ipn_obj.txn_id  # Speichern der Transaktions-ID
                order.save()
                
                logger.info(f"Order {order.order_id} status updated to paid and done.")
            elif payment_status == ST_PP_PENDING:
                order.payment_status = 'Pending'
                order.save()
                logging.info(f"Order {order_id} marked as pending.")
            else:
                # Zahlung fehlgeschlagen oder abgebrochen
                logging.warning(f"Order {order_id} received unknown payment status: {payment_status}")

        except Order.DoesNotExist:
            logging.error(f"Order with ID {order_id} not found.")
        except Exception as e:
            logging.error(f"Error processing IPN: {e}")

    return HttpResponse("IPN processed")


def payment_success(request):
    order_id = request.GET.get('order_id')
    try:
        order = Order.objects.get(order_id=order_id)
    except Order.DoesNotExist:
        return render(request, 'paypal/payment_error.html', {"message": "Order not found."})

    # Markiere die Bestellung als abgeschlossen und bezahlte Bestellung
    order.done = True
    order.paid = True
    order.payment_status = 'Payed'
    order.payment_id = request.GET.get('payment_id')  # Speichern der Transaktions-ID, falls verfügbar
    order.save()

    return render(request, 'paypal/payment_success.html', {"order": order})


def payment_cancelled(request):
    order_id = request.GET.get('order_id')
    try:
        order = Order.objects.get(order_id=order_id)
    except Order.DoesNotExist:
        return render(request, 'paypal/payment_error.html', {"message": "Order not found."})

    # Markiere die Bestellung als abgeschlossen und setze den Bezahlstatus auf False
    order.done = True
    order.paid = False
    order.payment_status = 'Cancelled'
    order.status = 'Cancelled'
    order.save()

    return render(request, 'paypal/payment_cancelled.html', {"order": order})


@login_required(login_url='login')
def order(request, id):
    try:
        order = Order.objects.get(order_id=id)
        complaint = Complaint.objects.filter(order=order).first()
    except Order.DoesNotExist:
        messages.error(request, "Bestellung nicht gefunden.")
        return redirect('shop')

    # Sicherstellen, dass order und customer existieren, bevor fortgefahren wird
    if not order:
        messages.error(request, "Bestellung nicht gefunden.")
        return redirect('shop')

    if request.user.is_superuser or is_admin_or_seller(request.user):
        articles = order.orderdarticle_set.all()
        ctx = {'articles': articles, 'order': order, 'complaint': complaint}
        return render(request, 'shop/order.html', ctx)
    elif order.customer and hasattr(order.customer, 'user') and request.user == order.customer.user:
        articles = order.orderdarticle_set.all()
        ctx = {'articles': articles, 'order': order, 'complaint': complaint}
        return render(request, 'shop/order.html', ctx)
    else:
        # Kunden-Validierung
        if not order.customer:
            messages.error(request, "Bestellung hat keinen zugeordneten Kunden.")
        elif not hasattr(order.customer, 'user'):
            messages.error(request, "Bestellungskunde hat keinen zugeordneten Benutzer.")
        elif request.user != order.customer.user:
            messages.error(request, "Sie sind nicht berechtigt, diese Bestellung anzusehen.")
        
        return redirect('shop')



def error404(request, exception):
    return render(request, 'shop/404.html')


@login_required
@user_passes_test(is_admin_or_seller)
def seller_dashboard(request):
    # Berechnungen und Daten für das Dashboard
    total_customers = Customer.objects.count()
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(done=True).count()
    pending_orders = Order.objects.filter(done=False).count()

    open_orders = Order.objects.filter(done=False).order_by('-order_date')
    if open_orders.exists():
        open_orders = open_orders.exclude(pk=open_orders.first().pk)

    total_revenue = OrderdArticle.objects.aggregate(total_revenue=Sum('article__price'))['total_revenue']
    total_items_sold = OrderdArticle.objects.aggregate(total_items_sold=Sum('quantity'))['total_items_sold']
    if total_revenue is None:
        total_revenue = 0
    if total_items_sold is None:
        total_items_sold = 0

    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_customers = Customer.objects.filter(user__date_joined__gte=thirty_days_ago).count()

    top_customers = Customer.objects.annotate(
        total_spent=Sum(
            ExpressionWrapper(
                F('order__orderdarticle__quantity') * F('order__orderdarticle__article__price'),
                output_field=FloatField()
            )
        )
    ).order_by('-total_spent')[:5]
    
    orders_per_customer = Customer.objects.annotate(order_count=Count('order')).order_by('-order_count')[:5]
    popular_categories = Category.objects.annotate(total_sold=Sum('article__orderdarticle__quantity')).order_by('-total_sold')[:5]

    articles = Article.objects.annotate(total_sold=Sum('orderdarticle__quantity')).order_by('-total_sold')[:5]
    orders_per_day = Order.objects.annotate(day=TruncDay('order_date')).values('day').annotate(total=Count('id')).order_by('-day')
    orders_per_week = Order.objects.annotate(week=TruncWeek('order_date')).values('week').annotate(total=Count('id')).order_by('-week')
    orders_per_month = Order.objects.annotate(month=TruncMonth('order_date')).values('month').annotate(total=Count('id')).order_by('-month')

    # Hinzufügen einer Variable zur Template-Context
    is_seller = request.user.groups.filter(name='Sellers').exists()

    ctx = {
        'open_orders': open_orders,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'total_revenue': total_revenue,
        'total_items_sold': total_items_sold,
        'new_customers': new_customers,
        'top_customers': top_customers,
        'orders_per_customer': orders_per_customer,
        'popular_categories': popular_categories,
        'articles': articles,
        'orders_per_day': orders_per_day,
        'orders_per_week': orders_per_week,
        'orders_per_month': orders_per_month,
        'is_seller': is_seller
    }

    return render(request, 'shop/seller_dashboard.html', ctx)


@login_required
def customer_dashboard(request):
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        customer = None

    if customer:
        orders = Order.objects.filter(customer=customer, done=True).order_by('-order_date')
        
        # Paginator hinzufügen
        paginator = Paginator(orders, 10)
        page_number = request.GET.get('page')
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Berechnung der gesamten Ausgaben des Kunden
        total_spent = orders.aggregate(Sum('orderdarticle__article__price'))['orderdarticle__article__price__sum'] or 0.00
        total_spent = round(total_spent, 2)
        
        # Anzeige der beliebtesten Artikel
        total_orders = orders.count()
        popular_articles = OrderdArticle.objects.filter(order__customer=customer).values('article__name', 'article_id').annotate(total_bought=Sum('quantity')).order_by('-total_bought')[:5]

        # Bestellhistorie des Kunden (nur die aktuelle Seite)
        order_status = [(order, "Abgeschlossen" if order.done else "Offen") for order in page_obj]

        ctx = {
            'customer': customer,
            'total_spent': total_spent,
            'total_orders': total_orders,
            'popular_articles': popular_articles,
            'order_status': order_status,
            'page_obj': page_obj,
        }

        return render(request, 'shop/customer_dashboard.html', ctx)
    else:
        return render(request, 'shop/customer_not_found.html')


def search_results(request):
    form = SearchForm(request.GET)
    query = request.GET.get('query', '')
    articleId = request.GET.get('articleId', '')

    article = None
    results = []

    if articleId:
        try:
            article = Article.objects.get(id=int(articleId))
        except (ValueError, Article.DoesNotExist):
            pass

    if query:
        results = Article.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )

    ctx = {
        'form': form,
        'results': results,
        'article': article,
    }

    if not article and not results:
        ctx['not_found'] = True

    return render(request, 'shop/search_results.html', ctx)


@receiver(pre_save, sender=Article)
def generate_article_number(sender, instance, **kwargs):
    if not instance.article_number:
        # Finde die höchste vorhandene ID
        last_article = Article.objects.order_by('-id').first()
        if last_article:
            last_number = int(last_article.article_number.split('-')[1])
            new_number = last_number + 1
        else:
            new_number = 1
        instance.article_number = f"A-{new_number:05d}"


@login_required
@user_passes_test(is_admin_or_seller)
def add_article(request):
    if request.method == 'POST':
        if 'reset' in request.POST:
            # Wenn der "Abbrechen"-Button geklickt wurde
            messages.info(request, 'Aktion abgebrochen.')
            return redirect('add_article')
        else:
            # Wenn der "Speichern"-Button geklickt wurde
            form = AddArticleForm(request.POST, request.FILES)
            if form.is_valid():
                article = form.save()
                messages.success(request, f'Artikel {article.name} erfolgreich angelegt!')
                return redirect('add_article')
    else:
        form = AddArticleForm()

    articles = Article.objects.all().order_by()
    paginator = Paginator(articles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'shop/add_article.html', {
        'form': form,
        'page_obj': page_obj,
        'articles': articles
    })


@login_required
@user_passes_test(is_admin_or_seller)
def edit_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)

    if request.method == 'POST':
        if 'reset' in request.POST:
            # Wenn der "Abbrechen"-Button geklickt wurde
            messages.info(request, 'Bearbeitung abgebrochen.')
            return redirect('add_article')
        else:
            # Wenn der "Speichern"-Button geklickt wurde
            form = EditArticleForm(request.POST, request.FILES, instance=article)
            if form.is_valid():
                form.save()
                messages.success(request, 'Artikel erfolgreich bearbeitet!')
                return redirect('add_article')
    else:
        form = EditArticleForm(instance=article)

    articles = Article.objects.all()
    paginator = Paginator(articles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'shop/add_article.html', {
        'form': form,
        'page_obj': page_obj,
        'articles': articles
    })


@login_required
@user_passes_test(is_admin_or_seller)
def add_category(request):
    if request.method == 'POST':
        if 'add_category' in request.POST:
            form = AddCategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Kategorie erfolgreich angelegt!')
                return redirect('add_category')

        elif 'delete_category' in request.POST:
            category_ids = request.POST.getlist('categories_to_delete')
            Category.objects.filter(id__in=category_ids).delete()
            messages.success(request, 'Kategorien erfolgreich gelöscht!')
            return redirect('add_category')

    else:
        form = AddCategoryForm()

    # Holen aller Kategorien
    categories = Category.objects.all().order_by('name')

    # Separieren der Hauptkategorien von den Kindkategorien
    top_level_categories = categories.filter(parent__isnull=True)

    ctx = {
        'form': form,
        'top_level_categories': top_level_categories,
        'categories': categories,
    }

    return render(request, 'shop/add_category.html', ctx)


def category_detail(request, pk):
    try:
        # Hole die Kategorie und ihre Artikel
        category = Category.objects.get(pk=pk)
        articles = Article.objects.filter(category=category)

        # Hole alle Hauptkategorien
        top_level_categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')

        # Berechne die Anzahl der Artikel für jede Kategorie
        for cat in top_level_categories:
            cat.calculate_num_articles = cat.num_articles

        # Holen Sie sich die IDs der Kindkategorien der aktuellen Kategorie
        child_ids = set(cat.id for cat in category.get_descendants())
        # Auch die ID der aktuellen Kategorie hinzufügen, falls sie als Hauptkategorie angezeigt wird
        child_ids.add(category.id)

        # Filtere Hauptkategorien aus, die bereits als Kindkategorien existieren
        filtered_categories = top_level_categories.exclude(id__in=child_ids)

        ctx = {
            'category': category,
            'articles': articles,
            'categories': filtered_categories,
            'child_categories': category.get_descendants()  # Alle Kinder der aktuellen Kategorie
        }
    except Category.DoesNotExist:
        return HttpResponseNotFound("Category not found")

    return render(request, 'shop/category_detail.html', ctx)


@login_required
@user_passes_test(is_admin_or_seller)
def delete_article_confirmation(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == "POST":
        article.delete()
        messages.success(request, "Artikel erfolgreich gelöscht!")
        return redirect('add_article')
    return render(request, 'shop/delete_article.html', {'article': article})


def article_detail(request, id):
    article = get_object_or_404(Article, id=id)
    ctx = {
        'article': article,
    }
    return render(request, 'shop/article_detail.html', ctx)


def imprint(request):
    return render(request, 'shop/legal/imprint.html')


def privacy(request):
    return render(request, 'shop/legal/privacy.html')


@login_required
@user_passes_test(is_admin_or_seller)
def pending_orders(request):
    # Abfragen für verschiedene Bestellstatus
    pending_orders = Order.objects.filter(status='Pending', address__isnull=False).exclude(payment_status='Payed').order_by('-order_date')
    pending_and_payed_orders = Order.objects.filter(
        payment_status='Payed',
        address__isnull=False
    ).exclude(
        status__in=['Dispatched', 'Delivered', 'complained', 'Completed', 'Cancelled']
    ).order_by('-order_date')    
    dispatched_orders = Order.objects.filter(status='Dispatched').order_by('-order_date')
    delivered_orders = Order.objects.filter(status='Delivered').order_by('-order_date')
    complained_orders = Complaint.objects.select_related('order__customer').filter(order__status='Complained').order_by('-created_at')
    cancelled_orders = Order.objects.filter(status='Cancelled').order_by('-order_date')

    if request.method == 'POST':
        # Debugging-Ausgabe: Überprüfe, welche POST-Daten gesendet wurden
        print(f"DEBUG: POST data received: {request.POST}")

        if 'tracking_number' in request.POST:
            # Formular zum Setzen des Status auf "dispatched" und Speichern der Tracking-Nummer
            form = TrackingNumberForm(request.POST)
            if form.is_valid():
                order_id = form.cleaned_data['order_id']
                tracking_number = form.cleaned_data['tracking_number']
                
                print(f"DEBUG: Setting order {order_id} to dispatched with tracking number {tracking_number}")
                
                try:
                    order = Order.objects.get(order_id=order_id, status='Pending')
                    order.status = 'Dispatched'
                    order.tracking_number = tracking_number
                    order.shipping_date = timezone.now()
                    order.save()
                except Order.DoesNotExist:
                    print(f"DEBUG: No Order found with order_id={order_id} and status='Pending'")
                    return HttpResponseNotFound("Order not found.")

                return redirect('pending_orders')
        elif 'order_id' in request.POST and 'tracking_number' not in request.POST:
            # Formular zum Setzen des Lieferdatums auf das aktuelle Datum und Status auf "Delivered"
            delivery_form = MarkDeliveredForm(request.POST)
            if delivery_form.is_valid():
                order_id = delivery_form.cleaned_data['order_id']
                
                print(f"DEBUG: Marking order {order_id} as delivered")

                try:
                    order = Order.objects.get(order_id=order_id, status='Dispatched')
                    order.status = 'Delivered'
                    order.delivery_date = timezone.now()
                    order.save()
                except Order.DoesNotExist:
                    print(f"DEBUG: No Order found with order_id={order_id} and status='Dispatched'")
                    return HttpResponseNotFound("Order not found.")

                return redirect('pending_orders')
            else:
                print(f"DEBUG: Delivery form is not valid. Errors: {delivery_form.errors}")
    else:
        form = TrackingNumberForm()
        delivery_form = MarkDeliveredForm()

    ctx = {
        'pending_orders': pending_orders,
        'pending_and_payed_orders': pending_and_payed_orders,
        'dispatched_orders': dispatched_orders,
        'delivered_orders': delivered_orders,
        'complained_orders': complained_orders,
        'cancelled_orders': cancelled_orders,
        'form': form,
        'delivery_form': delivery_form,
    }
    return render(request, 'shop/pending_orders.html', ctx)


@login_required
@user_passes_test(is_admin_or_seller)
def mark_delivered(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, order_id=order_id, status='Dispatched')
        order.status = 'Delivered'
        order.save()
        return redirect('pending_orders')
    return redirect('pending_orders')


@login_required
def customer_complaints(request):
    selected_order = None
    articles = OrderdArticle.objects.none()

    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            complaint = form.save(commit=False)
            order_id = request.POST.get('order_id')
            print("POST-Daten:", request.POST)
            print("Bestell-ID:", order_id)

            if order_id:
                try:
                    selected_order = Order.objects.get(id=order_id, customer__user=request.user)
                    complaint.order = selected_order
                    complaint.customer = request.user.customer
                except Order.DoesNotExist:
                    complaint.order = None
                    complaint.customer = None

            # Debugging-Ausgabe: Überprüfen der Artikel im Formular
            print("Artikel im Formular:", form.cleaned_data.get('articles'))

            complaint.save()
            form.save_m2m()

            # Debugging-Ausgabe: Überprüfen der gespeicherten Artikel
            print("Reklamation gespeichert mit Artikeln:")
            for article in complaint.articles.all():
                print(f"- {article.name}")

            return redirect('customer_complaints')
    else:
        search_form = OrderSearchForm(request.GET)
        orders = Order.objects.none()

        if search_form.is_valid():
            search_term = search_form.cleaned_data.get('search_term', '')
            orders = Order.objects.filter(order_id__icontains=search_term, customer__user=request.user)

            if orders.exists():
                selected_order = orders.first()
                articles = selected_order.orderdarticle_set.all()

        form = ComplaintForm(user=request.user, selected_order=selected_order)

    complaints = Complaint.objects.filter(order__in=orders).prefetch_related('articles')

    return render(request, 'shop/customer_complaints.html', {
        'form': form,
        'search_form': search_form,
        'complaints': complaints,
        'articles': articles,
        'selected_order': selected_order,
    })


@login_required
def search_order(request):
    if request.method == 'POST':
        search_id = request.POST.get('search_id')
        order = get_object_or_404(Order, order_id=search_id)
        return render(request, 'shop/complaint_form.html', {'order': order, 'form': ComplaintForm()})
    return render(request, 'shop/search_order.html')


@login_required
def complaint_form(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    
    # Überprüfen, ob bereits eine Reklamation für diese Bestellung existiert
    if Complaint.objects.filter(order=order).exists():
        # Optional: Fehlermeldung ausgeben oder weiterleiten
        messages.error(request, "Für diese Bestellung wurde bereits eine Reklamation eingereicht.")
        return redirect('order', id=order.order_id)

    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.order = order
            complaint.customer = order.customer
            complaint.save()
            
            # Update order status
            order.status = 'Complained'
            order.save()
            
            # Verknüpfen der Artikel zur Reklamation
            ordered_articles = order.get_ordered_articles()
            # Extrahieren der Artikel IDs
            article_ids = [article.article.id for article in ordered_articles]
            # Setzen der Artikel auf die Reklamation
            complaint.articles.set(article_ids)
            
            messages.success(request, "Reklamation erfolgreich mit ID " + str(complaint.id) + " eingereicht.")
            return redirect('order', id=order.order_id)
    else:
        form = ComplaintForm()

    # Retrieve ordered articles
    ordered_articles = OrderdArticle.objects.filter(order=order)

    return render(request, 'shop/complaint_form.html', {
        'form': form,
        'order': order,
        'ordered_articles': ordered_articles,
    })


def complaint_detail(request, complaint_id):
    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    order = get_object_or_404(Order, id=complaint.order.id)
    
    ctx = {
        'complaint': complaint,
        'order': order
    }
    
    return render(request, 'shop/complaint_detail.html', ctx)


def generate_pdf(request):
    if request.method == 'POST':
        try:
            # Daten aus dem Formular holen
            firma = request.POST.get('seller[personName]', '')
            seller_strasse_nr = request.POST.get('seller[address][streetNr]', '')
            seller_plz = request.POST.get('client[address][place]', '')
            rechnungsnummer = request.POST.get('invoiceNr', '')
            rechnungsdatum = request.POST.get('invoiceDate', '')
            kunde = request.POST.get('client[companyName]', '')
            adresse = request.POST.get('client[address][streetNr]', '') + ', ' + request.POST.get('client[address][place]', '')
            text_before = request.POST.get('textBefore', '')
            text_after = request.POST.get('textAfter', '')

            seller_bank_name = request.POST.get('seller[bankAccount][bankName]', '')
            seller_iban = request.POST.get('seller[bankAccount][iban]', '')
            seller_bic = request.POST.get('seller[bankAccount][bic]', '')
            seller_ustid = request.POST.get('seller[bankAccount][ustid]', '')
            seller_account_holder = request.POST.get('seller[bankAccount][accountHolder]', '')
            suggested_purpose = request.POST.get('suggestedPurpose', '')

            # Positionen abrufen
            positions = []
            added_positions = set()
            for key in request.POST:
                if key.startswith('positions'):
                    index = key.split('[')[1].split(']')[0]
                    if index.isdigit():
                        position = {
                            'position': request.POST.get(f'positions[{index}][position]', ''),
                            'description': request.POST.get(f'positions[{index}][description]', ''),
                            'quantity': request.POST.get(f'positions[{index}][quantity]', ''),
                            'unit': request.POST.get(f'positions[{index}][unit]', ''),
                            'unit_price': request.POST.get(f'positions[{index}][unitPrice]', ''),
                            'total_price': request.POST.get(f'positions[{index}][totalPrice]', ''),
                        }
                        # Debugging-Ausgabe
                        logger.debug(f"Verarbeite Position: {position}")

                        # Überprüfen, ob die Position bereits hinzugefügt wurde
                        position_tuple = tuple(position.items())
                        if position_tuple not in added_positions:
                            positions.append(position)
                            added_positions.add(position_tuple)

            # HTML-Inhalt erstellen
            html = render_to_string('pdf/invoice.html', {
                'seller_name': firma,
                'straße_nr': seller_strasse_nr,
                'plz': seller_plz,
                'rechnungsnummer': rechnungsnummer,
                'rechnungsdatum': rechnungsdatum,
                'kunde': kunde,
                'adresse': adresse,
                'positions': positions,
                'text_before': text_before,
                'text_after': text_after,
                'seller_bank_name': seller_bank_name,
                'seller_iban': seller_iban,
                'seller_bic': seller_bic,
                'seller_ustid': seller_ustid,
                'seller_account_holder': seller_account_holder,
                'suggested_purpose': suggested_purpose,
            })

            # PDF erstellen
            result = BytesIO()
            pdf = pisa.CreatePDF(html, dest=result)

            if pdf.err:
                logger.error(f"Fehler beim Erstellen der PDF: {pdf.err}")
                return HttpResponse("Ein Fehler ist beim Erstellen der PDF aufgetreten.")

            pdf_data = result.getvalue()

            # Order-Objekt abrufen oder erstellen
            try:
                order = Order.objects.get(pk=1)
            except Order.DoesNotExist:
                logger.error("Order-Objekt mit pk=1 existiert nicht.")
                return HttpResponse("Das benötigte Order-Objekt wurde nicht gefunden.")

            # Generieren der Rechnungs-ID außerhalb der Transaktion
            invoice_id = Invoice.get_next_invoice_id()
            invoice_filename = f"Rechnung_{invoice_id}.pdf"

            # Rechnung speichern innerhalb einer Transaktion
            try:
                with transaction.atomic():
                    invoice_instance = Invoice(
                        pdf=ContentFile(pdf_data, name=invoice_filename),
                        invoice_id=invoice_id,
                        order=order
                    )
                    invoice_instance.save()
            except IntegrityError:
                # Wenn es zu einem IntegrityError kommt, wird die Transaktion zurückgerollt
                logger.error(f"Rechnungs-ID {invoice_id} bereits vergeben.")
                messages.error(request, "Ein Fehler ist aufgetreten. Bitte versuchen Sie es später noch einmal.")
                return redirect('generate_pdf')  # Zurück zum Formular

            messages.success(request, "Rechnung erfolgreich erstellt.")

            # PDF herunterladen
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{invoice_filename}"'
            response.write(pdf_data)
            return response

        except IntegrityError as ie:
            logger.error(f"Integritätsfehler beim Speichern der Rechnung: {str(ie)}")
            messages.error(request, "Ein Integritätsfehler ist aufgetreten. Bitte versuchen Sie es später noch einmal.")
            return redirect('generate_pdf')
        except Exception as e:
            logger.error(f"Allgemeiner Fehler beim Verarbeiten der PDF-Erstellung oder beim Speichern der Rechnung: {str(e)}")
            messages.error(request, "Ein Fehler ist aufgetreten. Bitte versuchen Sie es später noch einmal.")
            return redirect('generate_pdf')

    # Formular anzeigen
    return render(request, 'pdf/index.html')


@login_required
def generate_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    # Prüfen, ob eine Rechnung für die Bestellung bereits existiert
    existing_invoice = Invoice.objects.filter(order=order).first()
    if existing_invoice:
        # Rechnung existiert bereits, zur Rechnungsseite umleiten
        return redirect('invoice_detail', invoice_id=existing_invoice.id)

    # Daten für die Rechnung sammeln
    customer = order.customer
    ordered_articles = OrderdArticle.objects.filter(order=order)
    address = Address.objects.filter(order=order).first()

    # Eine neue Rechnung erstellen
    invoice = Invoice.objects.create(
        invoice_id=Invoice.get_next_invoice_id(),
        customer=customer,
        order=order
    )
    
    # Bildpfad
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'header_invoice.jpg')

    # Bild in Base64 konvertieren
    with open(logo_path, 'rb') as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')

    # Template laden
    template_path = 'pdf/invoice_template.html'
    ctx = {
        'invoice': invoice,
        'order': order,
        'customer': customer,
        'ordered_articles': ordered_articles,
        'address': address,
        'base64_logo': base64_image,
    }

    # Render the HTML template to a string
    template = get_template(template_path)
    html = template.render(ctx)

    # Create a BytesIO buffer to receive the PDF output
    buffer = BytesIO()

    # Generate PDF from HTML
    pisa_status = pisa.CreatePDF(html, dest=buffer)

    # Check if there was an error
    if pisa_status.err:
        return HttpResponse('Fehler beim Erstellen der PDF-Datei: <pre>' + html + '</pre>')

    # Save the PDF in the buffer
    buffer.seek(0)
    # Save the buffer content to the FileField
    invoice.pdf.save(f'{invoice.invoice_id}.pdf', buffer, save=True)

    # Return a response with the PDF file
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="invoice_{invoice.invoice_id}.pdf"'

    return response


@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    order = invoice.order
    ordered_articles = OrderdArticle.objects.filter(order=order)
    address = Address.objects.filter(order=order).first()

    ctx = {
        'invoice': invoice,
        'order': order,
        'ordered_articles': ordered_articles,
        'address': address,
        'total_cost': order.get_cart_total(),
    }
    return render(request, 'pdf/invoice_detail.html', ctx)


@login_required
def generate_delivery_note(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    # Prüfen, ob ein Lieferschein für die Bestellung bereits existiert
    existing_note = DeliveryNote.objects.filter(order=order).first()
    if existing_note:
        # Lieferschein existiert bereits, zur Detailseite umleiten
        return redirect('delivery_note_detail', delivery_note_id=existing_note.id)

    # Daten für den Lieferschein sammeln
    customer = order.customer
    ordered_articles = OrderdArticle.objects.filter(order=order)
    address = Address.objects.filter(order=order).first()

    # Einen neuen Lieferschein erstellen
    delivery_note = DeliveryNote.objects.create(
        delivery_note_id=DeliveryNote.get_next_delivery_note_id(),
        customer=customer,
        order=order
    )
    
    # Bildpfad
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'header_delivery_note.jpg')

    # Bild in Base64 konvertieren
    with open(logo_path, 'rb') as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')

    # Template laden
    template_path = 'pdf/delivery_note_template.html'
    ctx = {
        'delivery_note': delivery_note,
        'order': order,
        'customer': customer,
        'ordered_articles': ordered_articles,
        'address': address,
        'base64_logo': base64_image,
    }

    # Render the HTML template to a string
    template = get_template(template_path)
    html = template.render(ctx)

    # Create a BytesIO buffer to receive the PDF output
    buffer = BytesIO()

    # Generate PDF from HTML
    pisa_status = pisa.CreatePDF(html, dest=buffer)

    # Check if there was an error
    if pisa_status.err:
        return HttpResponse('Fehler beim Erstellen der PDF-Datei: <pre>' + html + '</pre>')

    # Save the PDF in the buffer
    buffer.seek(0)
    # Save the buffer content to the FileField
    delivery_note.pdf.save(f'{delivery_note.delivery_note_id}.pdf', buffer, save=True)

    # Return a response with the PDF file
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="delivery_note_{delivery_note.delivery_note_id}.pdf"'

    return response


@login_required
def delivery_note_detail(request, delivery_note_id):
    delivery_note = get_object_or_404(DeliveryNote, id=delivery_note_id)
    order = delivery_note.order
    ordered_articles = OrderdArticle.objects.filter(order=order)
    address = Address.objects.filter(order=order).first()

    ctx = {
        'delivery_note': delivery_note,
        'order': order,
        'ordered_articles': ordered_articles,
        'address': address,
        'total_cost': order.get_cart_total(),
    }
    return render(request, 'pdf/delivery_note_detail.html', ctx)


def delete_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    if order.status == 'Pending':
        order.status = 'Cancelled'  # Status auf "Cancelled" setzen
        order.deleted = True        # Bestellung als gelöscht markieren
        order.save()
        messages.success(request, "Die Bestellung wurde erfolgreich als gelöscht markiert.")
    else:
        # Überprüfen Sie den Status der Bestellung und zeigen Sie die entsprechende Nachricht an
        if order.status == 'Cancelled':
            messages.error(request, "Diese Bestellung wurde bereits storniert.")
        elif order.status == 'Dispatched':
            messages.error(request, "Diese Bestellung wurde bereits versendet und kann nicht storniert werden.")
        elif order.status == 'complained':
            messages.error(request, "Diese Bestellung wurde bereits reklamiert und kann nicht storniert werden.")
        elif order.status == 'Completed':
            messages.error(request, "Diese Bestellung wurde bereits abgeschlossen und kann nicht storniert werden.")
        else:
            messages.error(request, "Diese Bestellung kann nicht storniert werden.")

    return redirect('order',  id=order.order_id)


@login_required
def update_shipping_status(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)  # hole die Order anhand der order_id

    # Adresse aus der Datenbank holen (erste Adresse der Bestellung verwenden oder None)
    address = order.address_set.first() if order.address_set.exists() else None

    # Artikel aus der Datenbank holen
    ordered_article = order.orderdarticle_set.first()
    article = ordered_article.article if ordered_article else None

    # Wenn die Methode POST ist, wird das Formular validiert und gesendet
    if request.method == 'POST':
        form = ShippingForm(request.POST)
        if form.is_valid():
            # Versende die Bestellung über DHL
            success = send_package_with_dhl(order)
            
            if success:
                order.shipment_status = 'Shipped'
                order.save()
                return redirect('order_detail', order_id=order.order_id)
            else:
                form.add_error(None, "Fehler beim Versand über DHL.")
    else:
        # Initialisiere das Formular mit den Daten aus der Bestellung
        initial_data = {
            'recipient_name': f"{order.customer.first_name} {order.customer.last_name}" if order.customer else '',
            'street_address': address.address if address else '',
            'city': address.city if address else '',
            'postal_code': address.zipcode if address else '',
            'country': address.country if address else '',
            'shipping_method': order.shipment_status,  # Beispiel wie die Versandart vorbelegt wird
            'tracking_number': order.tracking_number,
            'shipping_provider': order.shipping_provider,
            'shipping_date': order.shipping_date,
            'delivery_date': order.delivery_date,
            'weight': article.weight,
            'length': article.length,
            'height': article.height,
            'width': article.width,
            'volume': article.volume,
            'goods_value': order.get_cart_total(),
            # weitere Felder...
        }
        form = ShippingForm(initial=initial_data)

    return render(request, 'shop/update_shipping_status.html', {'form': form, 'order': order})


@login_required
@user_passes_test(is_admin_or_seller)
def send_message(request):
    if request.method == 'POST':
        # Empfänger, Betreff und Nachrichtentext aus den POST-Daten abrufen
        recipient_id = request.POST.get('recipient')
        subject = request.POST.get('subject')
        body = request.POST.get('body')

        # Den Empfänger basierend auf der Empfänger-ID abrufen
        recipient = get_object_or_404(User, id=recipient_id)
        
        # Nachricht erstellen und speichern
        message = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            subject=subject,
            body=body
        )
        message.save()

        # Umleitung zur Inbox nach dem Versenden
        return redirect('message_inbox')
    
    else:
        form = MessageForm()

    return render(request, 'shop/send_message.html', {'form': form})


@login_required
def message_inbox(request):
    # Nachrichten, bei denen der Benutzer entweder der Absender oder der Empfänger ist
    user_messages = Message.objects.filter(
        models.Q(sender=request.user) | models.Q(recipient=request.user)
    ).order_by('-sent_at')
    
    return render(request, 'shop/message_inbox.html', {'user_messages': user_messages})


@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    if message.recipient == request.user or message.sender == request.user:
        if message.recipient == request.user and message.read_at is None:
            message.mark_as_read()
        return render(request, 'shop/message_detail.html', {'message': message})
    else:
        return redirect('message_inbox')

@login_required
def reply_message(request, message_id):
    original_message = get_object_or_404(Message, id=message_id)
    
    if request.method == 'POST':
        form = MessageReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.sender = request.user
            reply.recipient = original_message.sender
            reply.subject = f"Re: {original_message.subject}"
            reply.save()
            return redirect('message_inbox')
    else:
        form = MessageReplyForm()
    
    return render(request, 'shop/reply_message.html', {'form': form, 'original_message': original_message})


@login_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    # Sicherstellen, dass der Benutzer der Absender oder Empfänger der Nachricht ist
    if message.sender == request.user or message.recipient == request.user:
        message.delete()
    
    return redirect('message_inbox')


@login_required
def chat_history(request, recipient_id):
    # Den Empfänger und alle Nachrichten zwischen Sender und Empfänger finden
    recipient = get_object_or_404(User, id=recipient_id)
    
    # Filterung der Nachrichten, die zwischen dem aktuellen Benutzer und dem Empfänger gesendet wurden
    chat_messages = Message.objects.filter(
        (models.Q(sender=request.user) & models.Q(recipient=recipient)) |
        (models.Q(sender=recipient) & models.Q(recipient=request.user))
    ).order_by('sent_at')  # Sortieren nach Sendedatum aufsteigend
    
    # Markiere alle ungelesenen Nachrichten als gelesen
    unread_messages = chat_messages.filter(recipient=request.user, read_at__isnull=True)
    unread_messages.update(read_at=timezone.now())
    
    if request.method == 'POST':
        form = MessageReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.sender = request.user
            reply.recipient = recipient
            reply.subject = f"Re: {chat_messages.last().subject}"  # Antwort auf die letzte Nachricht
            reply.save()
            return redirect('chat_history', recipient_id=recipient.id)
    else:
        form = MessageReplyForm()
    
    # Übergabe der `chat_messages` an das Template und nicht `messages`
    return render(request, 'shop/chat_history.html', {
        'chat_messages': chat_messages, 
        'form': form, 
        'recipient': recipient
    })


