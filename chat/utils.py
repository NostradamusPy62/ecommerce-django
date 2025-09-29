import os
import google.generativeai as genai
from django.conf import settings
from store.models import Product, Category
from orders.models import Order
from django.contrib.auth import get_user_model
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import io
from django.http import HttpResponse
from django.utils import timezone

class ChatBotUtils:

    def __init__(self):
        # Configurar Google AI - LEE DESDE SETTINGS
        
        # Intenta obtener la API Key de settings primero, luego de variables de entorno
        self.api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None)
        
        if not self.api_key:
            # Si no está en settings, busca en variables de entorno
            self.api_key = os.getenv('GOOGLE_AI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY no está configurada. "
                "Por favor, agrega GOOGLE_AI_API_KEY a tu archivo .env"
            )
        
        # Configurar Google Generative AI
        genai.configure(api_key=self.api_key)
        
        # Usar modelo estable directamente (gemini-pro-latest es el más confiable)
        try:
            self.model = genai.GenerativeModel('models/gemini-pro-latest')
            print("✅ Modelo gemini-pro-latest cargado correctamente")
        except Exception as e:
            print(f"❌ Error cargando gemini-pro-latest: {e}")
            
            # Fallback a gemini-pro si falla
            try:
                self.model = genai.GenerativeModel('models/gemini-pro')
                print("✅ Modelo gemini-pro cargado como fallback")
            except Exception as e2:
                print(f"❌ Error también con gemini-pro: {e2}")
                
                # Último intento con cualquier modelo disponible
                try:
                    available_models = self.list_available_models()
                    if available_models:
                        model_name = available_models[0]
                        self.model = genai.GenerativeModel(model_name)
                        print(f"✅ Modelo {model_name} cargado como último recurso")
                    else:
                        self.model = None
                        print("⚠️  No hay modelos disponibles, usando solo sistema de fallback")
                except Exception as e3:
                    self.model = None
                    print(f"❌ Error crítico: No se pudo cargar ningún modelo: {e3}")

    def list_available_models(self):
        """Lista los modelos disponibles para generateContent"""
        try:
            models = genai.list_models()
            available_models = []
            for model in models:
                if 'generateContent' in model.supported_generation_methods:
                    available_models.append(model.name)
            return available_models
        except Exception as e:
            print(f"Error al listar modelos: {e}")
            return ['gemini-pro']  # Fallback
    
    def get_system_prompt(self):
        """Define el prompt del sistema para el asistente"""
        return """
        Eres un asistente virtual especializado para un e-commerce. Tu propósito es ayudar a los usuarios con:

        1. Información de productos: precios, stock, descripciones, características
        2. Proceso de compra: cómo realizar pedidos, métodos de pago, envíos
        3. Estado de pedidos: seguimiento, historial
        4. Gestión de cuenta: inicio de sesión, registro, actualización de perfil, contraseñas
        5. Categorías de productos y búsqueda
        6. Políticas de la tienda: devoluciones, garantías, términos de servicio

        Reglas importantes:
        - Sé amable, profesional y útil
        - Si no tienes información suficiente, pide más detalles
        - Para consultas sobre stock específico o precios, verifica en la base de datos
        - Ignora mensajes sin sentido o no relacionados con la tienda
        - Para comparaciones de productos, proporciona información clara y objetiva
        - Siempre ofrece seguir ayudando después de cada respuesta
        - Responde en español
        - Sé conciso pero informativo
        """
    
    def get_product_info(self):
        """Obtiene información actualizada de productos para el contexto"""
        products = Product.objects.all().select_related('category')
        product_info = []
        
        for product in products:
            product_info.append({
                'id': product.id,
                'name': product.product_name,
                'price': float(product.price),
                'stock': product.stock,
                'category': product.category.category_name,
                'description': product.description
            })
        
        return product_info
    
    def get_categories_info(self):
        """Obtiene información de categorías"""
        categories = Category.objects.all()
        return [{
            'id': cat.id,
            'name': cat.category_name,
            'description': cat.description
        } for cat in categories]
    
    def generate_google_ai_response(self, user_message, conversation_history):
        """Genera respuesta usando Google AI API - Versión mejorada"""
        try:
            # Información actualizada de la tienda
            product_info = self.get_product_info()
            categories_info = self.get_categories_info()
            
            # Construir prompt más efectivo
            prompt = f"""
            Eres un asistente virtual especializado en e-commerce. Responde ÚNICAMENTE en español.
            
            INFORMACIÓN ACTUAL DE LA TIENDA:
            - Productos disponibles: {len(product_info)}
            - Categorías: {[cat['name'] for cat in categories_info]}
            - Datos de productos: {product_info}
            
            CONTEXTO DE USUARIO:
            - El usuario está en una tienda online real
            - Puedes acceder a información actualizada de productos, precios y stock
            - Debes ser útil, preciso y amable
            
            PREGUNTA DEL USUARIO: "{user_message}"
            
            Responde de manera:
            - Útil y específica basándote en los datos reales de la tienda
            - En español claro y natural
            - Incluye información relevante de productos si aplica
            - Ofrece seguir ayudando
            
            RESPUESTA:
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.7,
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"Error con Google AI, usando fallback: {e}")
            return self.generate_fallback_response(user_message)
    
    def generate_fallback_response(self, user_message):
        """Genera una respuesta de fallback más inteligente cuando la IA no funciona"""
        try:
            user_message_lower = user_message.lower()
            
            # 1. Consultas sobre productos por categoría
            if any(word in user_message_lower for word in ['categoría', 'categoria', 'computadoras', 'ropa', 'música', 'muebles', 'accesorios']):
                if 'computadora' in user_message_lower:
                    products = Product.objects.filter(category__category_name__icontains='computadora', is_available=True)
                    if products.exists():
                        product_list = "\n".join([f"• **{p.product_name}** - ${p.price} (Stock: {p.stock})" for p in products])
                        return f"🖥️ **Productos en Computadoras:**\n\n{product_list}\n\n¿Te interesa alguno de estos productos?"
                    else:
                        return "❌ No hay productos disponibles en la categoría Computadoras."
                
                # Para otras categorías
                categories = Category.objects.all()
                category_list = "\n".join([f"• {cat.category_name}" for cat in categories])
                return f"📂 **Categorías disponibles:**\n\n{category_list}\n\n" \
                    f"Puedo mostrarte los productos de cualquier categoría. ¿Cuál te interesa?"
            
            # 2. Consultas sobre presupuesto
            elif any(word in user_message_lower for word in ['presupuesto', 'gs', 'guaraníes', '200.000', '200000', 'dinero']):
                budget = 200000
                affordable_products = Product.objects.filter(price__lte=budget, is_available=True).order_by('price')
                
                if affordable_products.exists():
                    product_list = "\n".join([f"• **{p.product_name}** - ${p.price} (Stock: {p.stock})" for p in affordable_products])
                    return f"💰 **Productos dentro de tu presupuesto de {budget:,} GS:**\n\n{product_list}\n\n" \
                        f"¿Te gustaría más información de algún producto en particular?"
                else:
                    return f"❌ No hay productos dentro de tu presupuesto de {budget:,} GS. " \
                        f"El producto más económico cuesta ${Product.objects.filter(is_available=True).order_by('price').first().price}"
            
            # 3. Consultas sobre ayuda de cuenta
            elif any(word in user_message_lower for word in ['contraseña', 'password', 'cambiar contraseña', 'olvidé contraseña']):
                return "🔐 **Para cambiar tu contraseña:**\n\n" \
                    "1. Ve a 'Mi Cuenta' en el menú superior\n" \
                    "2. Haz clic en 'Cambiar Contraseña'\n" \
                    "3. Ingresa tu contraseña actual y la nueva\n" \
                    "4. Confirma los cambios\n\n" \
                    "Si olvidaste tu contraseña, haz clic en '¿Olvidaste tu contraseña?' en la página de login."
            
            # 4. Consultas sobre proceso de compra
            elif any(word in user_message_lower for word in ['comprar', 'pedido', 'carrito', 'pago', 'envío']):
                return "🛒 **Proceso de compra:**\n\n" \
                    "1. **Agregar productos**: Haz clic en 'Agregar al Carrito'\n" \
                    "2. **Ver carrito**: Ve a 'Carrito' en el menú\n" \
                    "3. **Checkout**: Haz clic en 'Proceder al Pago'\n" \
                    "4. **Envío**: Elige dirección y método de envío\n" \
                    "5. **Pago**: Selecciona tu método de pago\n" \
                    "6. **Confirmación**: Recibirás un email de confirmación\n\n" \
                    "¿En qué paso necesitas ayuda?"
            
            # 5. Consultas sobre stock específico
            elif any(word in user_message_lower for word in ['stock', 'disponible', 'cantidad', 'unidades']):
                products = Product.objects.all().order_by('-stock')
                if products.exists():
                    top_products = products[:3]  # Top 3 productos con más stock
                    product_list = "\n".join([f"• **{p.product_name}** - {p.stock} unidades" for p in top_products])
                    return f"📦 **Productos con mayor stock:**\n\n{product_list}\n\n" \
                        f"¿Quieres información detallada de algún producto?"
            
            # 6. Consulta general mejorada
            else:
                product_count = Product.objects.count()
                category_count = Category.objects.count()
                total_products = Product.objects.filter(is_available=True)
                
                # Productos destacados
                featured_products = total_products.order_by('?')[:3]  # 3 productos aleatorios
                
                featured_list = "\n".join([f"• **{p.product_name}** - ${p.price}" for p in featured_products])
                
                return f"¡Hola! Soy tu asistente virtual. 😊\n\n" \
                    f"**Resumen de la tienda:**\n" \
                    f"• {product_count} productos disponibles\n" \
                    f"• {category_count} categorías\n\n" \
                    f"**Algunos productos destacados:**\n{featured_list}\n\n" \
                    f"**Puedo ayudarte con:**\n" \
                    f"• 🛍️ Información de productos y stock\n" \
                    f"• 💰 Precios y presupuestos\n" \
                    f"• 🛒 Proceso de compra\n" \
                    f"• 🔐 Gestión de cuenta\n" \
                    f"• 📦 Seguimiento de pedidos\n" \
                    f"• 🔄 Comparación de productos\n\n" \
                    f"¿En qué necesitas ayuda específicamente?"
                            
        except Exception as e:
            return "¡Hola! Estoy aquí para ayudarte con información sobre nuestros productos, stock, precios, proceso de compra y gestión de tu cuenta. ¿En qué puedo asistirte hoy?"
    
    def generate_stock_pdf(self):
        """Genera PDF con el stock de productos"""
        try:
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            
            # Encabezado
            pdf.setTitle("Reporte de Stock - E-commerce")
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(100, 750, "Reporte de Stock de Productos")
            pdf.setFont("Helvetica", 10)
            pdf.drawString(100, 735, f"Generado el: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
            
            # Información de productos
            products = Product.objects.all().select_related('category').order_by('category__category_name', 'product_name')
            y_position = 700
            
            current_category = None
            for product in products:
                # Nueva categoría
                if product.category.category_name != current_category:
                    current_category = product.category.category_name
                    y_position -= 20
                    if y_position < 50:
                        pdf.showPage()
                        y_position = 750
                    pdf.setFont("Helvetica-Bold", 12)
                    pdf.drawString(100, y_position, f"Categoría: {current_category}")
                    y_position -= 15
                
                # Información del producto
                if y_position < 50:
                    pdf.showPage()
                    y_position = 750
                
                pdf.setFont("Helvetica", 10)
                product_line = f"  {product.product_name} - Stock: {product.stock} - Precio: ${product.price}"
                pdf.drawString(120, y_position, product_line)
                y_position -= 15
            
            pdf.save()
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            raise Exception(f"Error al generar PDF: {str(e)}")
    
    def compare_products(self, product_ids):
        """Compara productos usando IA cuando está disponible"""
        try:
            products = Product.objects.filter(id__in=product_ids).select_related('category')
            
            if len(products) < 2:
                return "Se necesitan al menos 2 productos para comparar"
            
            # Intentar con IA primero
            comparison_data = []
            for product in products:
                comparison_data.append({
                    'nombre': product.product_name,
                    'precio': float(product.price),
                    'categoría': product.category.category_name,
                    'stock': product.stock,
                    'descripción': product.description,
                })
            
            prompt = f"""
            Como experto en e-commerce, compara estos productos de manera útil:
            
            {comparison_data}
            
            Responde en español con:
            1. Similitudes clave
            2. Diferencias principales (precio, características)
            3. Recomendación según diferentes necesidades
            4. Mejor opción por categoría (valor, características)
            
            Sé objetivo y útil para el cliente:
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            print(f"Error en comparación con IA: {e}")
            # Fallback a comparación manual
            return self._manual_product_comparison(product_ids)