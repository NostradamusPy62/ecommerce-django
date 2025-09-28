import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from carts.models import CartItem
from store.models import Product
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
import datetime
import json
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa
import io

# Credenciales de PayPal (sandbox)
PAYPAL_CLIENT_ID = "Aa33v-HZKPm0B4-dXWFzGh1COaGfif5H59dL7_J4EZ3YSVvOaH7uH5r9BbEOzKWQNrWJPS1G9nl0N40M"
PAYPAL_SECRET = "EJ2yv_lMXnImAmPeTJKZtEC2ZcZgZkjh4asgJiZOVXU0mz0HvkVsgLb94igrs3OIPTQ8MxSCwlKNUb6S"
PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com"  # Usa api-m.paypal.com en producción


"""def payments(request):
    body = json.loads(request.body )
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])

    payment = Payment(
        user = request.user,
        payment_id = body['transID'],
        payment_method = body['payment_method'],
        amount_id = order.order_total,
        status = body['status'],
    )
    payment.save()

    order.payment = payment
    order.is_ordered = True
    order.save()



    return render(request, 'orders/payments.html')
"""

@csrf_exempt
def payments(request):
    """
    Guarda Payment y crea OrderProduct a partir de CartItems.
    Maneja variaciones correctamente con ManyToMany.
    """
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            order = get_object_or_404(Order, user=request.user, is_ordered=False, order_number=body['orderID'])

            # Crear Payment
            payment = Payment.objects.create(
                user=request.user,
                payment_id=body['transID'],
                payment_method=body['payment_method'],
                amount_id=order.order_total,
                status=body['status']
            )

            # Vincular pago con la orden
            order.payment = payment
            order.is_ordered = True
            order.save()

            # Traer todos los cart items del usuario
            cart_items = CartItem.objects.filter(user=request.user)
            print(f"DEBUG: cart_items encontrados = {cart_items.count()}")

            for item in cart_items:
                print(f"DEBUG: procesando CartItem id={item.id}, product={item.product.product_name}, quantity={item.quantity}")
                variations = item.variations.all()
                print(f"DEBUG: variations = {[v.variation_value for v in variations]}")

                # Crear OrderProduct sin color ni size
                order_product = OrderProduct.objects.create(
                    order=order,
                    payment=payment,
                    user=request.user,
                    product=item.product,
                    quantity=item.quantity,
                    product_price=item.product.price,
                    ordered=True
                )


                product = Product.objects.get(id=item.product_id)
                product.stock -= item.quantity
                product.save()

                # Asignar variaciones correctamente
                if variations.exists():
                    order_product.variation.set(variations)

                print(f"DEBUG: OrderProduct creado id={order_product.id}")

            # Limpiar el carrito
            cart_items.delete()
            print("DEBUG: Carrito limpiado")


            mail_subject = 'Gracias por tu compra!'
            body = render_to_string('orders/order_recieved_email.html', {
                'user': request.user,
                'order': order,
            })

            to_email = request.user.email
            send_email = EmailMessage(mail_subject, body, to=[to_email])
            send_email.send()


            return JsonResponse({'status': 'success', 'transID': payment.payment_id, 'order_number': order.order_number})

        except Exception as e:
            import traceback
            print("DEBUG: ERROR en payments:", e)
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return render(request, 'orders/payments.html')



def place_order(request, total=0, quantity=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()

    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    exchange_rate = 7150
    usd_total = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

    tax = (10 * total) / 100
    grand_total = total + tax
    usd_total = round(grand_total / exchange_rate, 2)

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.ruc = form.cleaned_data['ruc']
            data.addres_line_1 = form.cleaned_data['addres_line_1']
            data.addres_line_2 = form.cleaned_data['addres_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            current_date = datetime.date.today().strftime('%Y%m%d')
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

            context = {
                'order': order,
                'order_number': order_number,  # <--- esto es lo que falta
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
                'usd_total': usd_total,
                'exchange_rate': exchange_rate,
                'paypal_client_id': PAYPAL_CLIENT_ID,
            }


            return render(request, 'orders/payments.html', context)
    else:
        return redirect('checkout')


# -----------------------------
# PAYPAL INTEGRACIÓN REAL
# -----------------------------

def get_paypal_access_token():
    auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}

    r = requests.post(f"{PAYPAL_API_BASE}/v1/oauth2/token", headers=headers, data=data, auth=auth)
    return r.json()["access_token"]


@csrf_exempt
def paypal_create_order(request):
    if request.method == "POST":
        current_user = request.user
        cart_items = CartItem.objects.filter(user=current_user, is_active=True)

        total = sum([item.product.price * item.quantity for item in cart_items])
        tax = (10 * total) / 100
        grand_total = total + tax
        usd_total = round(grand_total / 7150, 2)

        access_token = get_paypal_access_token()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
        body = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(usd_total)
                }
            }]
        }

        r = requests.post(f"{PAYPAL_API_BASE}/v2/checkout/orders", headers=headers, json=body)
        return JsonResponse(r.json())


@csrf_exempt
def paypal_capture_order(request, order_id):
    if request.method == "POST":
        access_token = get_paypal_access_token()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}

        r = requests.post(f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture", headers=headers)
        return JsonResponse(r.json())


def order_complete(request, order_number):
    transID = request.GET.get('payment_id')  # opcional si lo pasás por URL query

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        order_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = sum([item.product_price * item.quantity for item in order_products])

        if transID:
            payment = Payment.objects.get(payment_id=transID)
        else:
            payment = order.payment  # fallback si no viene transID

        context = {
            'order': order,
            'ordered_products': order_products,
            'order_number': order.order_number,
            'transID': payment.payment_id,
            'payment': payment,
            'subtotal': subtotal
        }
        return render(request, 'orders/order_complete.html', context)

    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')


def generate_invoice_pdf(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, is_ordered=True)
    payment = order.payment

    # Armamos los ítems con subtotal
    items = []
    for item in order.orderproduct_set.all():
        subtotal = item.quantity * item.product_price
        items.append({
            'product_name': item.product.product_name,
            'quantity': item.quantity,
            'price': item.product_price,
            'subtotal': subtotal,
        })

    # Renderizamos el template HTML
    html = render_to_string('orders/invoice_pdf.html', {
        'order': order,
        'order_number': order.order_number,
        'payment': payment,
        'items': items,
    })

    # Creamos el PDF en memoria
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)

    if pisa_status.err:
        return HttpResponse('Ocurrió un error generando el PDF')

    # 📧 Enviar email con factura adjunta
    subject = f"Factura de tu compra #{order.order_number}"
    message = "Adjunto encontrarás la factura de tu compra. ¡Gracias por confiar en nosotros!"
    email = EmailMessage(
        subject,
        message,
        'no-reply@tuecommerce.com',  # Remitente (cambiar según tu config)
        [order.email],  # 📩 Email del comprador
    )
    email.attach(f"Factura_{order.order_number}.pdf", pdf_buffer.getvalue(), 'application/pdf')
    email.send()

    # Mostrar el PDF en el navegador también
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_{order.order_number}.pdf"'
    return response