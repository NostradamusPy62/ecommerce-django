from .models import Cart, CartItem
from .views import _cart_id


""" def counter(request):
    cart_count = 0

    try:  
        cart = Cart.objects.filter(cart_id=_cart_id(request)).first()

        if request.user.is_authenticated:
            cart_items = CartItem.objects.all().filter(user=request.user)
        else:

            cart_items = CartItem.objects.all().filter(cart=cart[:1])

        for cart_item in cart_items:
            cart_count += cart_item.quantity

    except Cart.DoesNotExist:
        cart_count = 0

    return dict(cart_count=cart_count)
"""

def counter(request):
    cart_count = 0
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user)
        else:
            cart = Cart.objects.filter(cart_id=_cart_id(request)).first()
            if cart:
                cart_items = CartItem.objects.filter(cart=cart)
            else:
                cart_items = []

        for cart_item in cart_items:
            cart_count += cart_item.quantity

    except:
        cart_count = 0

    return dict(cart_count=cart_count)
