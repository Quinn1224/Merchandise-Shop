# Register your models here.
from django.contrib import admin
from .models import (
    Product,
    ProductVariant,
    Size,
    Color,
    CustomizationOption,
    Order,
    OrderItem,
    EmailTemplate
)
from .forms import ColorForm

# Produkte
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'color')

# Anpassungsoptionen
class CustomizationOptionInLine(admin.TabularInline):
    model = CustomizationOption
    extra = 1
    fields = ('label', 'option_type', 'required', 'extra_price')

# Propdukte
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    prepopulated_fields = {'slug': ['name']}
    inlines = [ProductVariantInline, CustomizationOptionInLine]

# Groeßen
@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')
    form = ColorForm


# Bestellungen
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('quantity', 'variant', 'customization_details', 'get_item_total','price_at_purchase')
    extra = 0
    can_delete = False
    @admin.display(description='Gesamtpreis Position')
    def get_item_total(self, obj):
        if obj.pk:
            return f"{obj.total_price:.2f} €"
        return "0.00 €"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'get_total_price', 'is_order_payed', 'status', 'created', 'last_modified')
    readonly_fields = ('created', 'get_total_price')
    inlines = [OrderItemInline]

    @admin.display(description='Gesamtsumme')
    def get_total_price(self, obj):
        if obj.pk:
            return f"{obj.total_price:.2f} €"
        return "0.00 €"
    
@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'subject', 'active', 'last_modified')
    #readonly_fields = ['active']