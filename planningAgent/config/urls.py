from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Schema view configuration for Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="Planning Agent API",
        default_version='v1',
        description="API for calculating and exporting personal availability plans.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@planning.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin Interface
    path('admin/', admin.site.urls),

    # API Endpoints
    path('api/v1/', include('planningAgent.urls')),

    # Swagger Documentation Endpoints
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]