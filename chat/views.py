from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
import json
from reportlab.pdfgen import canvas  # ← AGREGAR ESTA IMPORTACIÓN
from reportlab.lib.pagesizes import letter
import io

from .models import ChatMessage
from .forms import ChatForm
from .utils import ChatBotUtils
from store.models import Product, Category

class ChatView(View):
    def get(self, request):
        """Vista principal del chat"""
        form = ChatForm()
        
        # Obtener historial de mensajes - CORREGIDO
        if request.user.is_authenticated:
            messages = ChatMessage.objects.filter(user=request.user).order_by('timestamp')[:20]
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            messages = ChatMessage.objects.filter(session_key=session_key).order_by('timestamp')[:20]
        
        context = {
            'form': form,
            'messages': messages,
            'categories': Category.objects.all()
        }
        return render(request, 'chat/chat.html', context)  # ← CORREGIDO: 'chat/chat.html'
    
    def post(self, request):
        """Procesar mensajes del chat"""
        form = ChatForm(request.POST)
        
        if form.is_valid():
            user_message = form.cleaned_data['message']
            chat_utils = ChatBotUtils()
            
            # Obtener historial de conversación reciente - CORREGIDO
            if request.user.is_authenticated:
                conversation_history = ChatMessage.objects.filter(
                    user=request.user
                ).order_by('timestamp')[:10]  # Orden ascendente
                session_key = None
            else:
                session_key = request.session.session_key
                if not session_key:
                    request.session.create()
                    session_key = request.session.session_key
                conversation_history = ChatMessage.objects.filter(
                    session_key=session_key
                ).order_by('timestamp')[:10]  # Orden ascendente
            
            # Convertir a formato para OpenAI
            history_list = []
            for msg in conversation_history:
                history_list.append({
                    'user_message': msg.user_message,
                    'bot_response': msg.bot_response
                })
            # NO se hace reverse() porque ya viene en orden cronológico correcto
            
            # Generar respuesta
            try:
                bot_response = chat_utils.generate_google_ai_response(user_message, history_list)
            except Exception as e:
                bot_response = f"Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta nuevamente. Error: {str(e)}"
            
            # Guardar en base de datos
            chat_message = ChatMessage(
                user=request.user if request.user.is_authenticated else None,
                user_message=user_message,
                bot_response=bot_response,
                session_key=session_key if not request.user.is_authenticated else ''
            )
            chat_message.save()
            
            return JsonResponse({
                'success': True,
                'user_message': user_message,
                'bot_response': bot_response,
                'timestamp': timezone.now().strftime('%H:%M')
            })
        
        return JsonResponse({'success': False, 'error': 'Formulario inválido'})

@method_decorator(csrf_exempt, name='dispatch')
class ProductsByCategoryView(View):
    def post(self, request):
        """Obtener productos por categoría"""
        try:
            data = json.loads(request.body)
            category_id = data.get('category_id')
            category_name = data.get('category_name')
            
            if category_id:
                products = Product.objects.filter(category_id=category_id, is_available=True)
            elif category_name:
                products = Product.objects.filter(category__category_name__icontains=category_name, is_available=True)
            else:
                return JsonResponse({'error': 'Se requiere category_id o category_name'}, status=400)
            
            products_data = []
            for product in products:
                # Manejo seguro de imágenes
                image_url = None
                try:
                    if hasattr(product, 'images') and product.images.exists():
                        image_url = product.images.first().image.url
                except Exception:
                    image_url = None
                
                products_data.append({
                    'id': product.id,
                    'name': product.product_name,
                    'price': str(product.price),
                    'stock': product.stock,
                    'description': product.description,
                    'image_url': image_url
                })
            
            return JsonResponse({
                'success': True,
                'products': products_data,
                'count': len(products_data)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class GenerateStockPDFView(View):
    def get(self, request):
        """Generar y descargar PDF de stock"""
        try:
            chat_utils = ChatBotUtils()
            pdf_buffer = chat_utils.generate_stock_pdf()
            
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="stock_report.pdf"'
            return response
            
        except Exception as e:
            # Fallback a PDF básico si hay error
            try:
                buffer = io.BytesIO()  # ← CORREGIDO: usar BytesIO en lugar de HttpResponse
                p = canvas.Canvas(buffer, pagesize=letter)
                p.setFont("Helvetica-Bold", 16)
                p.drawString(100, 800, "Reporte de Stock - E-commerce")
                
                y = 750
                products = Product.objects.filter(is_available=True).order_by('category__category_name', 'product_name')
                
                for product in products:
                    if y < 50:
                        p.showPage()
                        y = 800
                        p.setFont("Helvetica-Bold", 16)
                        p.drawString(100, 800, "Reporte de Stock - E-commerce (Cont.)")
                    
                    p.setFont("Helvetica", 10)
                    text = f"{product.product_name} - Stock: {product.stock} - Precio: ${product.price}"
                    p.drawString(50, y, text)
                    y -= 15
                
                p.save()
                buffer.seek(0)
                
                response = HttpResponse(buffer, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="stock_report.pdf"'
                return response
                
            except Exception as fallback_error:
                return JsonResponse({
                    'success': False, 
                    'error': f'Error al generar PDF: {str(e)}. Fallback también falló: {str(fallback_error)}'
                })

@method_decorator(csrf_exempt, name='dispatch')
class CompareProductsView(View):
    def post(self, request):
        """Comparar productos"""
        try:
            data = json.loads(request.body)
            product_ids = data.get('product_ids', [])
            
            if len(product_ids) < 2:
                return JsonResponse({
                    'success': False,
                    'error': 'Se necesitan al menos 2 productos para comparar'
                }, status=400)
            
            chat_utils = ChatBotUtils()
            comparison_result = chat_utils.compare_products(product_ids)
            
            return JsonResponse({
                'success': True,
                'comparison': comparison_result
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': f'Error al comparar productos: {str(e)}'
            })

def get_stock_list(request):
    """Obtener lista de stock para autocompletar o búsquedas"""
    try:
        products = Product.objects.filter(is_available=True).values('id', 'product_name', 'stock', 'price')
        
        stock_list = []
        for product in products:
            stock_list.append({
                'id': product['id'],
                'name': product['product_name'],
                'stock': product['stock'],
                'price': str(product['price']),
                'display': f"{product['product_name']} - Stock: {product['stock']} - ${product['price']}"
            })
        
        return JsonResponse({'products': stock_list})
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al obtener lista de stock: {str(e)}'
        })

# Mantener compatibilidad con las vistas antiguas si es necesario
@csrf_exempt
def chat_action(request):
    """Recibe acciones de botones: descargar PDF, comparar productos (para compatibilidad)"""
    data = json.loads(request.body)
    action = data.get('action')

    if action == "download_pdf":
        view = GenerateStockPDFView()
        return view.get(request)

    if action == "compare_products":
        product_ids = data.get('product_ids', [])
        data_body = json.dumps({'product_ids': product_ids})
        request._body = data_body.encode('utf-8')
        view = CompareProductsView()
        return view.post(request)

    return JsonResponse({"response": "Acción no reconocida."})