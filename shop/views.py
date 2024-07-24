import json
import uuid
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from . forms import CustomerCreationForm, SearchForm, AddArticleForm, AddCategoryForm, EditArticleForm, ProfileForm
from . models import *
from . viewtools import visitorCookieHandler, visitorOrder
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from paypal.standard.forms import PayPalPaymentsForm
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from urllib.parse import unquote

logging.basicConfig(level=logging.DEBUG)

def shop(request):
    categories = Category.objects.annotate(num_articles=Count('article')).order_by('name')
    
    articles = Article.objects.all()

    category_filter = request.GET.get('category')
    if category_filter:
        articles = Article.objects.filter(category__name=category_filter)
    else:
        articles = Article.objects.all()

    ctx = {
        'categories': categories,
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
    print(f"Data received: {data}")
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
            return redirect('shop')
        else:
            messages.error(request, 'Benutzername oder Passwort ungültig.')

    return render(request, 'shop/login.html', {'page': page})


def logoutUser(request):
    if request.user.is_authenticated:
        # Löschen der offene Bestellungen des aktuellen Benutzers
        # Order.objects.filter(customer=request.user.customer, done=False).delete()
    
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
            # Hier könntest du Code einfügen, um das Problem zu beheben
            # Zum Beispiel: Einen neuen Benutzer erstellen und mit dem Kunden verknüpfen
            # user = User.objects.create(username='neuer_benutzername', email='...')
            # customer.user = user
            # customer.save()
            print(f"Customer {customer.id} hat keine zugeordnete User-Instanz.")


def bestellen(request):
    try:
        order_id = uuid.uuid4()
        data = json.loads(request.body)
        logging.info(f"Received data: {data}")

        # Default cart_total value
        cart_total = 0.00

        # Server-side validation of required fields in customerData and deliveryAddress
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
                order = Order.objects.create(customer=customer, done=False, created_at=timezone.now())

            address_data = {
                'address': data['deliveryAddress']['address'],
                'zipcode': data['deliveryAddress']['zip'],
                'city': data['deliveryAddress']['city'],
                'state': data['deliveryAddress']['country'],
                'country': data['deliveryAddress']['country']
            }
            address, created = Adress.objects.update_or_create(
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

        order.order_id = order_id
        order.done = True
        order.save()

        paypal_dict = {
            "business": 'sb-n9yva31537598@business.example.com',
            "amount": format(cart_total, '.2f'),
            "invoice": str(order_id),
            "currency_code": "EUR",
            "notify_url": request.build_absolute_uri(reverse('paypal-ipn')),
            "return": request.build_absolute_uri(reverse('shop')),
            "cancel_return": request.build_absolute_uri(reverse('shop')),
        }

        paypal_form = PayPalPaymentsForm(initial=paypal_dict)

        order_url = str(order_id)
        messages.success(request, mark_safe(
            f"Vielen Dank für Ihre Bestellung: <a href='/order/{order_url}'>{order_url}</a>"
            "<br>Jetzt mit PayPal bezahlen:"
            f"<br>{paypal_form.render()}"
        ))

        response = HttpResponse('Bestellung erfolgreich')
        response.delete_cookie('cart')

        return response

    except ValueError as e:
        logging.error(f"ValueError: {e}")
        return HttpResponseBadRequest("Invalid input data")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return HttpResponseServerError("An unexpected error occurred")


@login_required(login_url='login')
def order(request, id):
    try:
        order = Order.objects.get(order_id=id)
    except Order.DoesNotExist:
        messages.error(request, "Bestellung nicht gefunden.")
        return redirect('shop')

    if request.user.is_superuser or (order.customer and order.customer.user == request.user):
        articles = order.orderdarticle_set.all()
        ctx = {'articles': articles, 'order': order}
        return render(request, 'shop/order.html', ctx)
    elif order.customer and hasattr(order.customer, 'user') and request.user == order.customer.user:
        articles = order.orderdarticle_set.all()
        ctx = {'articles': articles, 'order': order}
        return render(request, 'shop/order.html', ctx)
    else:
        if not order.customer:
            messages.error(request, "Bestellung hat keinen zugeordneten Kunden.")
        elif not hasattr(order.customer, 'user'):
            messages.error(request, "Bestellungskunde hat keinen zugeordneten Benutzer.")
        elif request.user != order.customer.user:
            messages.error(request, "Sie sind nicht berechtigt, diese Bestellung anzusehen.")
        
        return redirect('shop')


def error404(request, exception):
    return render(request, 'shop/404.html')


@login_required(login_url='login')
def admin_dashboard(request):
    total_customers = Customer.objects.count()
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(done=True).count()
    pending_orders = Order.objects.filter(done=False).count()
    
    # Alle offenen Bestellungen sortiert nach Bestelldatum in absteigender Reihenfolge abrufen
    open_orders = Order.objects.filter(done=False).order_by('-order_date')

    # Die letzte Bestellung aus der Liste entfernen
    if open_orders.exists():
        open_orders = open_orders.exclude(pk=open_orders.first().pk)

    # Gesamtumsatz berechnen
    total_revenue = OrderdArticle.objects.aggregate(total_revenue=Sum('article__price'))['total_revenue']
    if total_revenue is None:
        total_revenue = 0

    # Gesamtanzahl verkaufter Artikel berechnen
    total_items_sold = OrderdArticle.objects.aggregate(total_items_sold=Sum('quantity'))['total_items_sold']
    if total_items_sold is None:
        total_items_sold = 0

    # Anzahl neuer Kunden in den letzten 30 Tagen berechnen
    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_customers = Customer.objects.filter(user__date_joined__gte=thirty_days_ago).count()

    top_customers = Customer.objects.annotate(total_spent=Sum('order__orderdarticle__article__price') * Sum('order__orderdarticle__quantity')).order_by('-total_spent')[:5]
    orders_per_customer = Customer.objects.annotate(order_count=Count('order')).order_by('-order_count')[:5]
    popular_categories = Category.objects.annotate(total_sold=Sum('article__orderdarticle__quantity')).order_by('-total_sold')[:5]

    articles = Article.objects.annotate(total_sold=Sum('orderdarticle__quantity')).order_by('-total_sold')[:5]
    orders_per_day = Order.objects.annotate(day=TruncDay('order_date')).values('day').annotate(total=Count('id')).order_by('-day')
    orders_per_week = Order.objects.annotate(week=TruncWeek('order_date')).values('week').annotate(total=Count('id')).order_by('-week')
    orders_per_month = Order.objects.annotate(month=TruncMonth('order_date')).values('month').annotate(total=Count('id')).order_by('-month')

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
    }

    return render(request, 'shop/admin_dashboard.html', ctx)


@login_required
def customer_dashboard(request):
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        customer = None

    if customer:
        # Filterung der Bestellungen des Kunden
        orders = Order.objects.filter(customer=customer, done=True).order_by('-order_date')
        
        # Paginator hinzufügen
        paginator = Paginator(orders, 10)  # 10 Bestellungen pro Seite
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
            'page_obj': page_obj,  # Übergeben der paginierten Bestellungen an das Template
        }

        return render(request, 'shop/customer_dashboard.html', ctx)
    else:
        # Handle Fall, wenn der Kunde nicht gefunden wird
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


@login_required(login_url='login')
def add_article(request):    
    if not request.user.is_superuser:
        return redirect('shop')

    if request.method == 'POST':
        form = AddArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save()
            messages.success(request, 'Artikel erfolgreich angelegt!')
            return redirect('add_article')
    else:
        form = AddArticleForm()

    articles = Article.objects.all()
    paginator = Paginator(articles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'shop/add_article.html', {
        'form': form,
        'page_obj': page_obj, 
        'articles': articles
    })


@login_required(login_url='login')
def edit_article(request, article_id):
    if not request.user.is_superuser:
        return redirect('shop')

    article = get_object_or_404(Article, id=article_id)

    if request.method == 'POST':
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


@login_required(login_url='login')
def add_category(request):
    if not request.user.is_superuser:
        return redirect('shop')

    form = AddCategoryForm()
    categories = Category.objects.all().order_by('name')

    if request.method == 'POST':
        if 'add_category' in request.POST:
            form = AddCategoryForm(request.POST)
            if form.is_valid():
                categories_input = form.cleaned_data.get('categories')
                categories = [category.strip() for category in categories_input.split(',')]
                
                for category_name in categories:
                    Category.objects.get_or_create(name=category_name)

                messages.success(request, 'Kategorien erfolgreich angelegt!')
                return redirect('add_category')

        elif 'delete_category' in request.POST:
            category_ids = request.POST.getlist('categories_to_delete')
            Category.objects.filter(id__in=category_ids).delete()
            messages.success(request, 'Kategorien erfolgreich gelöscht!')
            return redirect('add_category')

    return render(request, 'shop/add_category.html', {'form': form, 'categories': categories})


@login_required
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