from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib import messages

from accounts.decorators import superadmin_required, admin_required, staff_required
from accounts.models import Account
from store.models import Product, Category, Variation
from orders.models import Order, OrderProduct, Payment
from chat.models import ChatMessage

@login_required
@staff_required
def dashboard(request):
    """Dashboard principal con métricas"""
    # Métricas generales
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.count()
    total_users = Account.objects.count()
    
    # Ventas del mes
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_sales = Order.objects.filter(
        created_at__month=current_month,
        created_at__year=current_year,
        status='Completed'
    ).aggregate(total=Sum('order_total'))['total'] or 0
    
    # Pedidos recientes
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # Productos con bajo stock
    low_stock_products = Product.objects.filter(stock__lte=10, is_available=True)[:5]
    
    # Estadísticas de pedidos por estado
    order_status_stats = Order.objects.values('status').annotate(count=Count('id'))
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_orders': total_orders,
        'total_users': total_users,
        'monthly_sales': monthly_sales,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
        'order_status_stats': order_status_stats,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)

# ========== GESTIÓN DE PRODUCTOS ==========
@login_required
@admin_required
def product_list(request):
    """Lista todos los productos"""
    products = Product.objects.select_related('category').all().order_by('-created_date')
    
    # Filtros
    category_filter = request.GET.get('category')
    stock_filter = request.GET.get('stock')
    
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    if stock_filter == 'low':
        products = products.filter(stock__lte=10)
    elif stock_filter == 'out':
        products = products.filter(stock=0)
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'admin_panel/products/list.html', context)

@login_required
@admin_required
def product_add(request):
    """Agregar nuevo producto"""
    categories = Category.objects.all()
    
    if request.method == 'POST':
        try:
            product_name = request.POST.get('product_name')
            slug = request.POST.get('slug')
            description = request.POST.get('description')
            price = request.POST.get('price')
            stock = request.POST.get('stock')
            category_id = request.POST.get('category')
            images = request.FILES.get('images')
            
            category = Category.objects.get(id=category_id)
            
            product = Product(
                product_name=product_name,
                slug=slug,
                description=description,
                price=price,
                stock=stock,
                category=category,
                is_available=True
            )
            
            if images:
                product.images = images
            
            product.save()
            messages.success(request, 'Producto agregado correctamente.')
            return redirect('admin_panel:product_list')
            
        except Exception as e:
            messages.error(request, f'Error al agregar producto: {str(e)}')
    
    context = {
        'categories': categories,
    }
    return render(request, 'admin_panel/products/add.html', context)

@login_required
@admin_required
def product_edit(request, product_id):
    """Editar producto existente"""
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        try:
            product.product_name = request.POST.get('product_name')
            product.slug = request.POST.get('slug')
            product.description = request.POST.get('description')
            product.price = request.POST.get('price')
            product.stock = request.POST.get('stock')
            product.category_id = request.POST.get('category')
            product.is_available = request.POST.get('is_available') == 'on'
            
            images = request.FILES.get('images')
            if images:
                product.images = images
            
            product.save()
            messages.success(request, 'Producto actualizado correctamente.')
            return redirect('admin_panel:product_list')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar producto: {str(e)}')
    
    context = {
        'product': product,
        'categories': categories,
    }
    return render(request, 'admin_panel/products/edit.html', context)

@login_required
@admin_required
def product_delete(request, product_id):
    """Eliminar producto"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product_name = product.product_name
        product.delete()
        messages.success(request, f'Producto "{product_name}" eliminado correctamente.')
        return redirect('admin_panel:product_list')
    
    return render(request, 'admin_panel/products/delete.html', {'product': product})

# ========== GESTIÓN DE CATEGORÍAS ==========
@login_required
@admin_required
def category_list(request):
    """Lista todas las categorías"""
    categories = Category.objects.all().order_by('category_name')
    return render(request, 'admin_panel/categories/list.html', {'categories': categories})

@login_required
@admin_required
def category_add(request):
    """Agregar nueva categoría"""
    if request.method == 'POST':
        try:
            category_name = request.POST.get('category_name')
            description = request.POST.get('description')
            slug = request.POST.get('slug')
            cat_image = request.FILES.get('cat_image')
            
            category = Category(
                category_name=category_name,
                description=description,
                slug=slug
            )
            
            if cat_image:
                category.cat_image = cat_image
            
            category.save()
            messages.success(request, 'Categoría agregada correctamente.')
            return redirect('admin_panel:category_list')
            
        except Exception as e:
            messages.error(request, f'Error al agregar categoría: {str(e)}')
    
    return render(request, 'admin_panel/categories/add.html')

@login_required
@admin_required
def category_edit(request, category_id):
    """Editar categoría existente"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        try:
            category.category_name = request.POST.get('category_name')
            category.description = request.POST.get('description')
            category.slug = request.POST.get('slug')
            
            cat_image = request.FILES.get('cat_image')
            if cat_image:
                category.cat_image = cat_image
            
            category.save()
            messages.success(request, 'Categoría actualizada correctamente.')
            return redirect('admin_panel:category_list')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar categoría: {str(e)}')
    
    return render(request, 'admin_panel/categories/edit.html', {'category': category})

@login_required
@admin_required
def category_delete(request, category_id):
    """Eliminar categoría"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        category_name = category.category_name
        category.delete()
        messages.success(request, f'Categoría "{category_name}" eliminada correctamente.')
        return redirect('admin_panel:category_list')
    
    return render(request, 'admin_panel/categories/delete.html', {'category': category})

# ========== GESTIÓN DE PEDIDOS ==========
@login_required
@staff_required
def order_list(request):
    """Lista todos los pedidos"""
    orders = Order.objects.select_related('user', 'payment').all().order_by('-created_at')
    
    # Filtros
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'status_choices': Order.STATUS,
    }
    return render(request, 'admin_panel/orders/list.html', context)

@login_required
@staff_required
def order_detail(request, order_id):
    """Detalle de pedido"""
    order = get_object_or_404(Order, id=order_id)
    order_products = OrderProduct.objects.filter(order=order).select_related('product')
    
    context = {
        'order': order,
        'order_products': order_products,
    }
    return render(request, 'admin_panel/orders/detail.html', context)

@login_required
@staff_required
def order_update_status(request, order_id):
    """Actualizar estado del pedido"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        order.status = new_status
        order.save()
        messages.success(request, f'Estado del pedido #{order.order_number} actualizado a {new_status}.')
    
    return redirect('admin_panel:order_detail', order_id=order_id)

# ========== GESTIÓN DE USUARIOS (SOLO SUPERADMIN) ==========
@login_required
@superadmin_required
def user_list(request):
    """Lista todos los usuarios"""
    users = Account.objects.all().order_by('-date_joined')
    return render(request, 'admin_panel/users/list.html', {'users': users})

@login_required
@superadmin_required
def user_edit_role(request, user_id):
    """Editar roles de usuario"""
    user = get_object_or_404(Account, id=user_id)
    
    if request.method == 'POST':
        try:
            user.is_staff = request.POST.get('is_staff') == 'on'
            user.is_admin = request.POST.get('is_admin') == 'on'
            user.is_superadmin = request.POST.get('is_superadmin') == 'on'
            user.is_active = request.POST.get('is_active') == 'on'
            
            user.save()
            messages.success(request, f'Roles de {user.email} actualizados correctamente.')
            return redirect('admin_panel:user_list')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar roles: {str(e)}')
    
    return render(request, 'admin_panel/users/edit_role.html', {'user': user})

# ========== REPORTES ==========
@login_required
@staff_required
def sales_report(request):
    """Reporte de ventas"""
    # Ventas por mes (últimos 6 meses) - SOLUCIÓN CORREGIDA para SQLite
    end_date = timezone.now()
    start_date = end_date - timedelta(days=180)
    
    # Consulta compatible con SQLite - VERSIÓN CORREGIDA
    monthly_sales = []
    try:
        monthly_sales = Order.objects.filter(
            created_at__range=[start_date, end_date],
            status='Completed'
        ).extra(select={
            'month': "strftime('%%m', created_at)",
            'year': "strftime('%%Y', created_at)"
        }).values('month', 'year').annotate(
            total_sales=Sum('order_total'),
            order_count=Count('id')
        ).order_by('year', 'month')
    except Exception as e:
        print(f"Error en consulta de ventas: {e}")
        # Fallback: datos básicos
        total_sales = Order.objects.filter(
            created_at__range=[start_date, end_date],
            status='Completed'
        ).aggregate(total=Sum('order_total'))['total'] or 0
        monthly_sales = [{
            'month': 'N/A', 
            'year': 'N/A', 
            'total_sales': total_sales,
            'order_count': Order.objects.filter(
                created_at__range=[start_date, end_date],
                status='Completed'
            ).count()
        }]
    
    # Productos más vendidos
    top_products = []
    try:
        top_products = OrderProduct.objects.filter(
            ordered=True
        ).values('product__product_name').annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum('product_price')
        ).order_by('-total_sold')[:10]
    except Exception as e:
        print(f"Error en consulta de productos: {e}")
    
    context = {
        'monthly_sales': monthly_sales,
        'top_products': top_products,
    }
    return render(request, 'admin_panel/reports/sales.html', context)

@login_required
@staff_required
def products_report(request):
    """Reporte de productos"""
    # Productos por categoría
    products_by_category = Product.objects.values(
        'category__category_name'
    ).annotate(
        product_count=Count('id'),
        total_stock=Sum('stock'),
        avg_price=Avg('price')
    )
    
    # Productos sin stock
    out_of_stock = Product.objects.filter(stock=0, is_available=True)
    
    # Productos con bajo stock
    low_stock = Product.objects.filter(stock__lte=10, stock__gt=0, is_available=True)
    
    context = {
        'products_by_category': products_by_category,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
    }
    return render(request, 'admin_panel/reports/products.html', context)

@login_required
@superadmin_required
def users_report(request):
    """Reporte de usuarios"""
    # Usuarios por mes - SOLUCIÓN CORREGIDA para SQLite
    users_by_month = []
    try:
        users_by_month = Account.objects.extra(select={
            'month': "strftime('%%m', date_joined)",
            'year': "strftime('%%Y', date_joined)"
        }).values('month', 'year').annotate(
            user_count=Count('id')
        ).order_by('year', 'month')[:12]
    except Exception as e:
        print(f"Error en consulta de usuarios: {e}")
        # Fallback: datos básicos
        users_by_month = [{
            'month': 'N/A',
            'year': 'N/A', 
            'user_count': Account.objects.count()
        }]
    
    # Estadísticas de roles
    role_stats = {
        'total_users': Account.objects.count(),
        'staff_users': Account.objects.filter(is_staff=True).count(),
        'admin_users': Account.objects.filter(is_admin=True).count(),
        'superadmin_users': Account.objects.filter(is_superadmin=True).count(),
        'active_users': Account.objects.filter(is_active=True).count(),
    }
    
    context = {
        'users_by_month': users_by_month,
        'role_stats': role_stats,
    }
    return render(request, 'admin_panel/reports/users.html', context)

# ========== CHAT HISTORY ==========
@login_required
@staff_required
def chat_history(request):
    """Historial de chat de usuarios"""
    # Obtener base query - SIN SLICE INICIAL
    chat_messages_query = ChatMessage.objects.select_related('user').order_by('-timestamp')
    
    # Filtros - APLICAR ANTES del slice
    user_filter = request.GET.get('user')
    if user_filter:
        chat_messages_query = chat_messages_query.filter(user_id=user_filter)
    
    # Aplicar slice DESPUÉS de los filtros
    chat_messages = chat_messages_query[:100]
    
    users = Account.objects.filter(chatmessage__isnull=False).distinct()
    
    context = {
        'chat_messages': chat_messages,
        'users': users,
    }
    return render(request, 'admin_panel/chat/history.html', context)