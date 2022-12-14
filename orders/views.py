import datetime
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from store.models import Product
from carts.models import CartItem
from orders.models import Order, OrderProduct, Payment
from .forms import OrderForm
import json
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
# Create your views here.


def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user,is_ordered=False,order_number=body['orderID'])
    payment = Payment(
        user = request.user,
        payment_method = body['payment_method'],
        amount_paid = order.order_total,
    )
    payment.save() #create payment
    order.payment = payment
    order.is_ordered = True #modify status order
    order.save()

    # move the cart item to order product table 
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.payment = payment
        orderproduct.user_id = request.user.id
        orderproduct.product_id = item.product_id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variation.set(product_variation)
        orderproduct.save()  #create OrderProduct



        # reduce quantity of the sold product 
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity  #set stock
        product.save()

    # clear cart 
    CartItem.objects.filter(user=request.user).delete()  #delete cart
    # send order email to customer
    mail_subject = "Thank you for your order!"
    message = render_to_string('orders/order_recieved_email.html', {
        'user': request.user,
        'order':order,
    })

    to_email = request.user.email #set to user
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send() #send email
    
    # send order number and id payment back to send data method via js
    data = {
        'order_number':order.order_number,
        'transID':payment.id,
    }

    return JsonResponse(data)

#  Handle empty cart -> return to shop
# Handle grand total by calculate tax and price
def place_order(request, total=0, quantity=0,):
    current_user = request.user

    # if the cart count is less than or equal to 0, then redirect back to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price*cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2*total)/100
    grand_total = total+tax

    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            # Get all user information
            # Store all the billing information inside Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            # Generate order includes user information,billing information
            # generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime('%Y%m%d')  # 20220414
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False,order_number=order_number)
            context = {
                'order':order,
                'cart_items':cart_items,
                'total':total,
                'tax':tax,
                'grand_total':grand_total,
            }
            # return all order information to payment success
            return render(request,'orders/payments.html',context)
        else:
            return redirect('checkout')


def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('transID')
    try:
        order = Order.objects.get(order_number=order_number,is_ordered = True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)
        payment = Payment.objects.get(id=transID)
        subtotal = 0
        for i in ordered_products:
            subtotal+=i.product_price*i.quantity
        context ={
            'order':order,
            'ordered_products':ordered_products,
            'order_number':order.order_number,
            'transID':payment.id,
            'subtotal':subtotal,
        }

        return render(request,'orders/order_complete.html',context)
    except (Payment.DoesNotExist,Order.DoesNotExist):
        return redirect('store')
# feat 60 1
# feat 60 2
# fear 60 3 

# feat 61 1
# feat 61 2



