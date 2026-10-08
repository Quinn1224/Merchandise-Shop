from django.db import models

# Produktmodell
class Product(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name='Name')
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, verbose_name='Beschreibung')
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Preis')
    image = models.ImageField(upload_to='shop/products', verbose_name='Bild')
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')
    class Meta:
        verbose_name="Produkt"
        verbose_name_plural = "Produkte"

    def __str__(self):
        return self.name    

#Groessenmodell
class Size(models.Model):
    name = models.CharField(max_length=30, unique=True, verbose_name='Name')
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')
    class Meta:
        verbose_name="Größe"
        verbose_name_plural = "Größen"

    def __str__(self):
        return self.name    

#Farbmodell
class Color(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Name')
    hex_code = models.CharField(max_length=7, blank=True, verbose_name='Hexadezimalcode')
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')
    class Meta:
        verbose_name="Farbe"
        verbose_name_plural = "Farben"
    def __str__(self):
        return self.name

#Produktvariantenmodell
class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        related_name='variants',
        on_delete=models.CASCADE
    )
    size = models.ForeignKey(
        Size,
        related_name='sizes',
        on_delete=models.PROTECT
    )
    color = models.ForeignKey(
        Color,
        related_name='colors',
        on_delete=models.PROTECT
    )
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'size', 'color'],
                name='unique_product_variant'
            )
        ]
        verbose_name="Produktvariante"
        verbose_name_plural = "Produktvarianten"

    def __str__(self):
        return f'{self.product.name} - {self.color.name} - {self.size.name}'

#Anpassungsoptionsmodell
class CustomizationOption(models.Model):
    OPTION_TYPES = [
        ('text', 'Text'),
        ('number', 'Zahl'),
        ('checkbox', 'Ja/Nein'),
    ]

    name = models.CharField(max_length=100, verbose_name='Name')
    product = models.ForeignKey(Product, related_name='options', on_delete=models.PROTECT)
    option_type = models.CharField(max_length=20, choices=OPTION_TYPES, verbose_name='Optionstyp')
    required = models.BooleanField(default=False, verbose_name='Pflichtfeld?')
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Preis')
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')
    class Meta:
           verbose_name="Personalisierungsoption"
           verbose_name_plural = "Personalisierungsoptionen"
    def __str__(self):
        return f'{self.product.name} - {self.name}'   

#Berstellungsmodell
class Order(models.Model):
    ORDER_STATE_TYPES = [
        ('ordered', 'Bestellung eingegangen'),
        ('ready_for_pickup', 'Bereit zur Abholung'),
        ('ready_for_shipment', 'Bereit zum Versand'),
        ('cancelled', 'Storniert'),
        ('completed', 'Abgeschlossen'),
    ]
    full_name = models.CharField(max_length=100, verbose_name='Vollständiger Name')
    email = models.EmailField()
    notes = models.TextField(blank=True, verbose_name='Anmerkung')   
    status = models.CharField(max_length=20, choices=ORDER_STATE_TYPES, default=ORDER_STATE_TYPES[0], verbose_name='Bestellstatus')
    is_order_payed = models.BooleanField(
        default=False,
        verbose_name='Bestellung bezahlt?',
        choices=[(True, 'Bezahlt'), (False, 'Zahlung ausstehend')],
    )
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')

    class Meta():
        verbose_name = 'Bestellung'
        verbose_name_plural = 'Bestellungen'
    
    #Berechnet den Gesamtwert aller Positionen dieser Bestellung.
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
    
    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"
    
# Bestellpositionsmodell
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        ProductVariant,
        related_name='order_items',
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='Menge')
    customization_details = models.JSONField(default=dict, blank=True, verbose_name='Personalisierungsdetails')
    price_at_purchase = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Gesamtpreis')
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')
    
    class Meta():
           verbose_name = 'Bestellposition'
           verbose_name_plural = 'Bestellpositionen'

    #Berechnet den Gesamtpreis aus den einzelnen Positionen
    @property
    def total_price(self):
        if self.quantity and self.price_at_purchase:
            return self.quantity * self.price_at_purchase
        return 0

    def __str__(self):
        return f'{self.quantity}x {self.variant}'  

# E-Mail Templatemodell
class EmailTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('order_confirmation', 'Bestellbestätigung'),
        ('invoice', 'Rechnung'),
    ]
    name = models.CharField(max_length=50, verbose_name='Name')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, verbose_name='Vorlagentyp', default=TEMPLATE_TYPES[0])
    subject = models.CharField(max_length=255, verbose_name='Betreff')
    txt_content = models.TextField(verbose_name='Textinhalt')
    html_content = models.TextField(verbose_name='HTML-Inhalt')
    active = models.BooleanField(default=False, verbose_name='Aktives Template?')
    last_modified = models.DateTimeField(auto_now=True, verbose_name='Zuletzt editiert')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungszeitpunkt')
    class Meta():
        verbose_name = 'E-Mail Template'
        verbose_name_plural = 'E-Mail Templates'

    def save(self, *args, **kwargs):
        EmailTemplate.objects.filter(
            template_type=self.template_type
        ).exclude(pk=self.pk).update(active=False)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f'{self.name}'  
