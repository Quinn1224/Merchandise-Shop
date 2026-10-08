from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin', RedirectView.as_view(url='admin/')),
    path('', include('merchandiseshop.urls', namespace='merchandiseshop')),
    path('captcha/', include('captcha.urls')),
    path('impressum/', TemplateView.as_view(template_name='impressum.html'), name='impressum'),
    path('datenschutz/', TemplateView.as_view(template_name='datenschutz.html'), name='datenschutz'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)