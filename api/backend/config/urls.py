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

    # REST API (consumida pelo frontend React)
    path('api/v1/', include('apps.api.urls', namespace='api')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "DATAcare Admin"
admin.site.site_title = "DATAcare Administration"
admin.site.index_title = "Welcome to DATAcare Administration"
