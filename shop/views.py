import json
import uuid
import logging
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from . forms import CustomerCreationForm, CustomerProfileForm, SearchForm, AddArticleForm, AddCategoryForm, EditArticleForm
from . models import *
from . viewtools import visitorCookieHandler, visitorOrder
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from paypal.standard.forms import PayPalPaymentsForm


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


def is_cookie_accepted(request, group_id):
    cookie_consent = request.COOKIES.get('cookie_consent', '')
    return group_id in cookie_consent.split(',')


def warenkorb(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, done=False)
        articles = order.orderdarticle_set.all()
    else:
        if is_cookie_accepted(request, 'essential'):
            cookiedata = visitorCookieHandler(request)
            articles = cookiedata['articles']
            order = cookiedata['order']
        else:
            articles = []
            order = None

    ctx = {'articles': articles, 
           'order': order,
           'articles': articles,
        }
    return render(request, 'shop/warenkorb.html', ctx)

def kasse(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, done=False)
        articles = order.orderdarticle_set.all()
    else:
        if is_cookie_accepted(request, 'essential'):
            cookiedata = visitorCookieHandler(request)
            articles = cookiedata['articles']
            order = cookiedata['order']
        else:
            articles = []
            order = None

    ctx = {'articles': articles, 
           'order': order,
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
            return redirect('shop')
        else:
            messages.error(request, 'Benutzername oder Passwort ungültig.')

    return render(request, 'shop/login.html', {'page': page})

def logoutUser(request):
    logout(request)
    return redirect('shop')

def regUser(request):
    page = 'reg'
    user_form = CustomerCreationForm()
    profile_form = CustomerProfileForm()

    if request.method == 'POST':
        user_form = CustomerCreationForm(request.POST)
        profile_form = CustomerProfileForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            customer = Customer.objects.create(user=user)

            if 'profile_picture' in request.FILES:
                customer.profile_picture = request.FILES['profile_picture']
                customer.save()

            login(request, user)
            messages.success(request, f'Benutzer {user.username} wurde erfolgreich erstellt.')
            return redirect('shop')
        else:
            error_messages = []
            if not user_form.is_valid():
                error_messages.extend(user_form.errors.values())
            if not profile_form.is_valid():
                error_messages.extend(profile_form.errors.values())
            for error in error_messages:
                messages.error(request, error)

    ctx = {'user_form': user_form, 'profile_form': profile_form, 'page': page}
    return render(request, 'shop/registration_form.html', ctx)

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

        if request.user.is_authenticated:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(customer=customer, done=False)
        else:
            customer, order = visitorOrder(request, data)

        # Sicherstellen, dass das Komma durch einen Punkt ersetzt wird
        cart_total_str = data['customerData']['cart_total'].replace(',', '.')
        cart_total = float(cart_total_str)

        order.order_id = order_id
        order.done = True
        order.save()

        Adress.objects.create(
            customer=customer,
            order=order,
            address=data['deliveryAdress']['adress'],
            zipcode=data['deliveryAdress']['zip'],
            city=data['deliveryAdress']['city'],
            state=data['deliveryAdress']['country'],
        )

        paypal_dict = {
            "business": 'sb-n9yva31537598@business.example.com',
            "amount": format(cart_total, '.2f'),
            #"item_name": "name of the item",
            "invoice": order_id,
            "currency_code": "EUR",
            "notify_url": request.build_absolute_uri(reverse('paypal-ipn')),
            "return": request.build_absolute_uri(reverse('shop')),
            "cancel_return": request.build_absolute_uri(reverse('shop')),
        }

        paypalForm = PayPalPaymentsForm(initial=paypal_dict)

        orderURL = str(order_id)
        messages.success(request, mark_safe("Vielen Dank für ihre <a href='/order/" + orderURL + "'>Bestellung: " + orderURL + "</a><br> Jetzt mit Paypal bezahlen: " + paypalForm.render()))
        # return JsonResponse("Bestellung erfolgreich", safe=False)
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

    if request.user.is_superuser:
        articles = order.orderdarticle_set.all()
        ctx = {'articles': articles, 'order': order}
        return render(request, 'shop/order.html', ctx)
    elif order.customer and hasattr(order.customer, 'user') and request.user == order.customer.user:
        articles = order.orderdarticle_set.all()
        ctx = {'articles': articles, 'order': order}
        return render(request, 'shop/order.html', ctx)
    else:
        # Füge Debugging-Informationen hinzu
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
    articles = Article.objects.all()
    
    # Gesamtzahl der Kunden
    total_customers = Customer.objects.count()

    # Gesamtzahl der Bestellungen
    total_orders = Order.objects.count()

    # Abgeschlossene und nicht abgeschlossene Bestellungen
    completed_orders = Order.objects.filter(done=True).count()
    pending_orders = Order.objects.filter(done=False).count()

    # Gesamtumsatz
    total_revenue = Order.objects.filter(done=True).aggregate(Sum('orderdarticle__article__price'))['orderdarticle__article__price__sum']
    total_revenue = round(total_revenue, 2) if total_revenue else 0

    # Anzahl der verkauften Artikel
    total_items_sold = OrderdArticle.objects.aggregate(Sum('quantity'))['quantity__sum']

    # Durchschnittlicher Bestellwert
    total_orders_value = Order.objects.filter(done=True).aggregate(Sum('orderdarticle__article__price'))['orderdarticle__article__price__sum']
    average_order_value = total_orders_value / completed_orders if completed_orders > 0 else 0
    average_order_value = round(average_order_value, 2)

    # Top-Kunden nach Umsatz
    top_customers = Customer.objects.annotate(total_spent=Sum('order__orderdarticle__article__price')).order_by('-total_spent')[:5]

    # Bestellungen pro Kunde
    orders_per_customer = Customer.objects.annotate(order_count=Count('order')).order_by('-order_count')

    # Beliebteste Kategorien (nach verkauften Artikeln)
    popular_categories = Article.objects.values('category__name').annotate(total_sold=Sum('orderdarticle__quantity')).order_by('-total_sold')[:5]

    # Neue Kunden (z.B. in den letzten 30 Tagen)
    last_30_days = timezone.now() - timedelta(days=30)
    new_customers = Customer.objects.filter(user__date_joined__gte=last_30_days).count()
    
    # Beliebteste Artikel (nach verkauften Artikeln)
    popular_articles = OrderdArticle.objects.values('article__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:5]
    
    # Bestellungen pro Tag/Woche/Monat
    from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
    orders_per_day = Order.objects.annotate(day=TruncDay('order_date')).values('day').annotate(total=Count('id')).order_by('day')
    orders_per_week = Order.objects.annotate(week=TruncWeek('order_date')).values('week').annotate(total=Count('id')).order_by('week')
    orders_per_month = Order.objects.annotate(month=TruncMonth('order_date')).values('month').annotate(total=Count('id')).order_by('month')

    # Gesamtzahl der Artikel
    total_articles = Article.objects.count()

    ctx = {
        'articles': articles,
        'popular_articles': popular_articles,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'total_revenue': total_revenue,
        'total_items_sold': total_items_sold,
        'average_order_value': average_order_value,
        'top_customers': top_customers,
        'orders_per_customer': orders_per_customer,
        'popular_categories': popular_categories,
        'new_customers': new_customers,
        'orders_per_day': orders_per_day,
        'orders_per_week': orders_per_week,
        'orders_per_month': orders_per_month,
        'total_articles': total_articles,
    }

    return render(request, 'shop/admin_dashboard.html', ctx)

@login_required
def customer_dashboard(request):
    customer = Customer.objects.get(user=request.user)
    # Nur Bestellungen mit order_id abrufen
    orders = Order.objects.filter(customer=customer).exclude(order_id=None)

    total_spent = round(orders.aggregate(Sum('orderdarticle__article__price'))['orderdarticle__article__price__sum'], 2)
    total_orders = orders.count()
    popular_articles = OrderdArticle.objects.filter(order__customer=customer).values('article__name', 'article_id').annotate(total_bought=Sum('quantity')).order_by('-total_bought')[:5]
    
    # Bestellhistorie (sortiert nach Datum)
    orders = Order.objects.filter(customer=customer, done=True).order_by('-order_date')

    # Bestellstatus hinzufügen
    order_status = []
    for order in orders:
        status = "Abgeschlossen" if order.done else "Offen"
        order_status.append((order, status))

    ctx = {
        'customer': customer,
        'orders': orders,
        'total_spent': total_spent,
        'total_orders': total_orders,
        'popular_articles': popular_articles,
        'order_status': order_status,
    }

    return render(request, 'shop/customer_dashboard.html', ctx)

def articleDetail(request, id):
    article = get_object_or_404(Article, id=id)
    ctx = {
        'article': article,
    }
    return render(request, 'shop/article_detail.html', ctx)

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

    return render(request, 'shop/add_article.html', {'form': form, 
                                                     'page_obj': page_obj, 
                                                     'articles': articles})
    
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

    return render(request, 'shop/add_article.html', {'form': form, 
                                                     'page_obj': page_obj, 
                                                     'articles': articles})
    

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


@login_required
def article_detail(request, article_id):
    article = get_object_or_404(Article, pk=article_id)


    # Render der Template-Datei
    return render(request, 'shop/article_detail.html', {
        'article': article,
    })


def imprint(request):
    return render(request, 'shop/legal/imprint.html')

def privacy(request):
    return render(request, 'shop/legal/privacy.html')