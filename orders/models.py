from django.db import models
from accounts.models import Account
from store.models import Product, Variation
from django.utils import timezone

# ===============================
# MODELOS EXISTENTES (modificados)
# ===============================

class Payment(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=100)
    amount_id = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.payment_id
    

class Order(models.Model):
    STATUS = (
        ('New', 'Nuevo'),
        ('Accepted', 'Aceptado'),
        ('Completed', 'Completado'),
        ('Cancelled', 'Cancelado'),
    )

    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    order_number = models.CharField(max_length=20)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=50)
    email = models.CharField(max_length=50)
    addres_line_1 = models.CharField(max_length=100)
    addres_line_2 = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    order_note = models.CharField(max_length=100, blank=True)
    order_total = models.FloatField(default=0.0)
    tax = models.FloatField(default=0.0)
    status = models.CharField(max_length=50, choices=STATUS, default='New')
    ip = models.CharField(blank=True, max_length=20)
    is_ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    ruc = models.CharField(max_length=20, blank=True, null=True, verbose_name="RUC")
    
    # NUEVOS CAMPOS PARA FACTURACIÓN
    numero_factura = models.CharField(max_length=20, blank=True, null=True)
    timbrado = models.CharField(max_length=8, blank=True, null=True)
    fecha_emision = models.DateTimeField(default=timezone.now)  # CORREGIDO: default en lugar de auto_now_add

    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def full_address(self):
        return f'{self.addres_line_1} {self.addres_line_2}'
    
    # NUEVO MÉTODO PARA GENERAR FACTURA
    def generar_numero_factura(self):
        if not self.numero_factura:
            numeracion = NumeracionFactura.objects.first()
            if numeracion:
                self.numero_factura = numeracion.obtener_siguiente_numero()
                timbrado_activo = Timbrado.objects.filter(activo=True).first()
                if timbrado_activo:
                    self.timbrado = timbrado_activo.numero
                self.save()
        return self.numero_factura

    def __str__(self):
        return self.first_name
    

class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation = models.ManyToManyField(Variation, blank=True)
    quantity = models.IntegerField()
    product_price = models.FloatField(default=0.0)
    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product.product_name

    # NUEVA PROPIEDAD PARA CALCULAR SUBTOTAL
    @property
    def subtotal(self):
        return self.product_price * self.quantity


# ===============================
# NUEVOS MODELOS DE FACTURACIÓN
# ===============================

class ConfiguracionEmpresa(models.Model):
    nombre = models.CharField(max_length=200, default="DavBorn Store")
    ruc = models.CharField(max_length=20, default="6771099-0")
    direccion = models.TextField(default="Km5 Monday Presidente Franco")
    telefono = models.CharField(max_length=50, default="+595 984 538502")
    email = models.EmailField(default="surubi991@gmail.com")
    actividad_economica = models.CharField(
        max_length=200, 
        default="Comercio de productos electronicos, oficina, gaming, etc"
    )
    
    class Meta:
        verbose_name = "Configuración Empresa"
        verbose_name_plural = "Configuración Empresa"
    
    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        # Permitir solo una configuración de empresa
        if not self.pk and ConfiguracionEmpresa.objects.exists():
            # Si ya existe una configuración, actualizar esa en lugar de crear nueva
            existing_config = ConfiguracionEmpresa.objects.first()
            existing_config.nombre = self.nombre
            existing_config.ruc = self.ruc
            existing_config.direccion = self.direccion
            existing_config.telefono = self.telefono
            existing_config.email = self.email
            existing_config.actividad_economica = self.actividad_economica
            existing_config.save()
            return existing_config
        return super().save(*args, **kwargs)


class Timbrado(models.Model):
    numero = models.CharField(max_length=8, default="12345678")
    fecha_inicio = models.DateField(default=timezone.now)  # CORREGIDO: default
    fecha_fin = models.DateField(default=timezone.now)     # CORREGIDO: default
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Timbrado {self.numero}"
    
    class Meta:
        verbose_name = "Timbrado"
        verbose_name_plural = "Timbrados"


class NumeracionFactura(models.Model):
    punto_emision = models.CharField(max_length=3, default="001")
    caja = models.CharField(max_length=3, default="001")
    numero_actual = models.IntegerField(default=1)
    
    def obtener_siguiente_numero(self):
        numero_str = str(self.numero_actual).zfill(8)
        self.numero_actual += 1
        self.save()
        return f"{self.punto_emision}-{self.caja}-{numero_str}"
    
    def __str__(self):
        return f"Numeración {self.punto_emision}-{self.caja}"
    
    class Meta:
        verbose_name = "Numeración Factura"
        verbose_name_plural = "Numeración Facturas"
    
    def save(self, *args, **kwargs):
        # Permitir solo una numeración
        if not self.pk and NumeracionFactura.objects.exists():
            existing_numeracion = NumeracionFactura.objects.first()
            existing_numeracion.punto_emision = self.punto_emision
            existing_numeracion.caja = self.caja
            existing_numeracion.numero_actual = self.numero_actual
            existing_numeracion.save()
            return existing_numeracion
        return super().save(*args, **kwargs)