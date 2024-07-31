from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def admin_or_seller_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser or (hasattr(request.user, 'customer') and request.user.customer.is_seller):
            return view_func(request, *args, **kwargs)
        else:
            return redirect('shop')
    return _wrapped_view