from pathlib import Path
from django.shortcuts import render, get_object_or_404, redirect
from django.template import Template, Context
from django.views.decorators.http import require_POST
from django.core.mail import EmailMultiAlternatives
from .models import Product, Order, OrderItem, ProductVariant, EmailTemplate
from .cart import Cart
from django.utils import timezone
from captcha.models import CaptchaStore
from captcha.helpers import captcha_image_url

# Übersichtsseite: Listet alle verfügbaren Merchandise-Artikel auf.
def product_list(request):
    products = Product.objects.all()
    return render(request, "merchandiseshop/product_list.html", {'products': products})

# Detailseite zu einem Artikel
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    options = product.options.all()

    # Gruppiere Varianten nach Größe, damit der Nutzer erst eine Größe und danach eine Farbe wählen kann.
    from collections import defaultdict
    variants_by_size = defaultdict(list)
    for variant in product.variants.all():
        variants_by_size[variant.size.id].append({
            'id': variant.id,
            'size': variant.size.name,
            'size_id': variant.size.id,
            'color': variant.color.name,
            'color_id': variant.color.id,
        })

    sizes = [
        {'id': size_id, 'name': variants_by_size[size_id][0]['size']}
        for size_id in sorted(variants_by_size.keys())
    ]

    # Konvertiere die Integer-Schlüssel zu Strings für JavaScript
    variants_by_size_str = {str(k): v for k, v in variants_by_size.items()}

    if request.method == 'POST':
        cart = Cart(request)
        quantity = int(request.POST.get('quantity', 1))
        variant_id = request.POST.get('variant_id')
        
        # Variant muss vorhanden sein - Fehlerbehandlung
        if not variant_id:
            return render(request, 'merchandiseshop/product_detail.html', {
                'product': product,
                'options': options,
                'sizes': sizes,
                'colors': [],
                'variants_by_size': variants_by_size_str,
                'error': 'Bitte wählen Sie eine Farbe und Größe aus.',
            })
        
        variant = product.variants.filter(pk=variant_id).first()
        if not variant:
            return render(request, 'merchandiseshop/product_detail.html', {
                'product': product,
                'options': options,
                'sizes': sizes,
                'colors': [],
                'variants_by_size': variants_by_size_str,
                'error': 'Die ausgewählte Variante ist nicht verfügbar.',
            })

        # Dynamische Erfassung der eingegebenen Personalisierungsoptionen
        customizations = {}
        for opt in options:
            val = request.POST.get(f'option_{opt.id}')
            if val:
                customizations[opt.name] = val

        # Variant ist garantiert ein Objekt (nicht None)
        cart.add(
            product=product,
            quantity=quantity,
            variant=variant,
            customizations=customizations
        )
        return redirect('merchandiseshop:cart_detail')
    
    return render(request, 'merchandiseshop/product_detail.html', {
        'product': product,
        'options': options,
        'sizes': sizes,
        'colors': [],
        'variants_by_size': variants_by_size_str,
    })

# Warenkorb-Übersichtsseite: Zeigt alle hinzugefügten Artikel und Personalisierungen.
def cart_detail(request):
    cart = Cart(request)
    return render(request, 'merchandiseshop/cart_detail.html', {'cart' : cart})

# Löscht einen Artikel aus dem Cart
@require_POST
def cart_remove(request, item_id):
    cart = Cart(request)
    cart.remove(item_id)
    return redirect('merchandiseshop:cart_detail')



# Erfasst Adressdaten und generiert die Bestellung
def checkout(request):
    cart = Cart(request)
    if request.method == 'POST':
        privacy_accepted = request.POST.get('privacy_accepted') == 'on'
        captcha_response = request.POST.get('captcha_response', '').strip().lower()
        captcha_hashkey = request.POST.get('captcha_hashkey', '')

        #Captcha aus der DB holen
        captcha_valid = False
        try:
            # Holt den DB-Eintrag zum Hash
            store = CaptchaStore.objects.get(
                hashkey=captcha_hashkey, 
                expiration__gt=timezone.now()
            )
            
            # Vergleicht die Nutzereingabe mit der gespeicherten Antwort
            if store.response == captcha_response:
                captcha_valid = True
            # Nach Verwendung aus der DB löschen (Replay-Schutz)
            store.delete()
        except CaptchaStore.DoesNotExist:
            # Falls Hash ungültig oder Captcha abgelaufen ist
            captcha_valid = False  

        # Datenschutz prüfen
        if not privacy_accepted:
            return handle_error(request, 'Bitte akzeptiere die Datenschutzerklärung.', cart)
        # Captcha prüfen
        elif not captcha_valid:
            return handle_error(request, 'Die Sicherheitsabfrage war falsch. Bitte erneut versuchen.', cart)
        # Bestellung abwickeln 
        else:
            return handle_order(request, cart)
       
    # GET Request
    new_hashkey = CaptchaStore.generate_key()
    return render(request, 'merchandiseshop/checkout.html', {
        'cart': cart,
        'captcha_hashkey': new_hashkey,
        'captcha_image_url': captcha_image_url(new_hashkey),
    })


# Behandelt Fehler bei der Bestellungsaufgabe
def handle_error(request, message, cart):
    new_hashkey = CaptchaStore.generate_key()
    context = {
        'cart': cart,
        'error': message,
        'captcha_hashkey': new_hashkey,
        'captcha_image_url': captcha_image_url(new_hashkey),
        'form_data': request.POST
    }
    return render(request, 'merchandiseshop/checkout.html', context)

# Erzeugt eine Bestellung im System und sendet eine Bestellbestätigung per Mail
def handle_order(request, cart):
    order_data = {
                'full_name': request.POST.get('full_name'),
                'email': request.POST.get('email'),
                'notes': request.POST.get('notes', ''),
            }
    for field in Order._meta.concrete_fields:
        if field.name in order_data or field.primary_key:
            continue
        if field.name in request.POST:
            order_data[field.name] = request.POST.get(field.name)
    try:
        order = Order.objects.create(**order_data)
    except Exception:
        return handle_error(request, 'Es wurde keine Bestellung erstellt. Bitte versuchen Sie es später erneut.', cart)
                
    if not order:
        return handle_error(request, 'Es wurde keine Bestellung erstellt. Bitte versuchen Sie es später erneut.', cart)
        
    for item in cart:
        variant_id = item.get('variant_id')
        variant = None
        if variant_id:
            variant = ProductVariant.objects.filter(pk=variant_id).first()
        err = OrderItem.objects.create(
            order=order,
            variant=variant,
            quantity=item['quantity'],
            customization_details=item['customizations'],
            price_at_purchase=item['price']
        )
        #Check ob ein Objekt angelegt wurde
        if not err:
            return handle_error(request, 'Ein Bestellposten konnte nicht angelegt werden. Bitte versuchen Sie es erneut.', cart)
            
            
    context = {
        'order': order,
        'cart': cart,
    }
    latest_template = (
        EmailTemplate.objects
        .filter(template_type='order_confirmation', active=True)
        .first()
    )
    
    if not latest_template:
        return handle_error(request, 'Es wurde keine Bestellung erstellt. Es konnte kein freigegebenes E-Mail Template für die Bestellbestätigung gefunden werden.', cart)
    # E-Mail versand vorbereiten
    text_content = Template(latest_template.txt_content).render(Context(context))
    html_content = Template(latest_template.html_content).render(Context(context))
    subject = Template(latest_template.subject).render(Context(context))
    from_email=None
    recipient_list=[order.email]
    msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    cart.clear()     
    return render(request, 'merchandiseshop/order_success.html', {'order': order})

