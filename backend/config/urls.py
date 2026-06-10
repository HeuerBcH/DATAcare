"""
Django URL Configuration for DATAcare project.
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from apps.users.urls import auth_api_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth JWT endpoints
    path('api/v1/auth/', include((auth_api_urlpatterns, 'auth'))),

    # Triagem (domínio ACS — coração do MVP)
    path('api/v1/triage/', include('apps.triage.urls')),

    # REST API endpoints
    path('api/v1/', include('apps.api.urls', namespace='api')),

    # MVT template views
    path('users/', include('apps.users.urls', namespace='users')),
    path('patients/', include('apps.patients.urls', namespace='patients')),
    path('predictions/', include('apps.predictions.urls', namespace='predictions')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "DATAcare Admin"
admin.site.site_title = "DATAcare Administration"
admin.site.index_title = "Welcome to DATAcare Administration"
