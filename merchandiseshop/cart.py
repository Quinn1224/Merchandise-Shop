import hashlib
import json
from decimal import Decimal

#Klasse muss nicht in die Datenbank, daher hier definiert
class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, product, variant, customizations, quantity=1):
        if quantity <= 0:
            return

        normalized_customizations = customizations or {}
        
        # Extrahiere nur die benötigten Daten aus dem Variant-Objekt
        variant_data = {
            'id': variant.id,
            'size': variant.size.name,
            'size_id': variant.size.id,
            'color': variant.color.name,
            'color_id': variant.color.id,
        }
        
        item_id = f"{product.id}_{variant.size.name}_{variant.color.name}_{hashlib.md5(json.dumps(normalized_customizations, sort_keys=True).encode()).hexdigest()}"
        # Berechne Customization-Preise basierend auf den verfügbaren Options
        customization_price = Decimal('0.00')
        for option in product.options.all():
            if option.name in normalized_customizations:
                customization_price += option.price

        if item_id not in self.cart:
            self.cart[item_id] = {
                'product_id': product.id,
                'quantity': 0,
                'variant': variant_data,
                'variant_id' : variant.id,
                'price': str(product.price),
                'customizations': normalized_customizations,
                'customization_price': str(customization_price),
                'product_name': product.name,
            }

        self.cart[item_id]['quantity'] += quantity
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, item_id):
        if item_id in self.cart:
            del self.cart[item_id]
            self.save()

    def clear(self):
        self.session['cart'] = {}
        self.save()

    #Macht Warenkorb iterierbar z. B. (for item in cart)
    def __iter__(self):
        for item_id, item in self.cart.items():
            item_price = Decimal(item['price']) + Decimal(item.get('customization_price', '0.00'))
            yield {
                'product_name': item['product_name'],
                'item_id': item_id,
                'product_id': item['product_id'],
                'quantity': item['quantity'],
                'variant': item['variant'],
                'variant_id': item['variant']['id'],
                'price': Decimal(item['price']),
                'customization_price': Decimal(item.get('customization_price', '0.00')),
                'total_price': item_price * item['quantity'],
                'customizations': item['customizations'],
            }

    def get_total_price(self):
        total = Decimal('0.00')
        for item in self.cart.values():
            item_price = Decimal(item['price']) + Decimal(item.get('customization_price', '0.00'))
            total += item_price * item['quantity']
        return total

    def get_tax_price(self):
        return self.get_total_price() * Decimal('0.19')

    def get_total_price_including_tax(self):
        return self.get_total_price() + self.get_tax_price()

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())