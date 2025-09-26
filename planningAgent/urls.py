# planning/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    HomeView,
    CalendarEntryViewSet,
    AvailabilityReportViewSet
)
router = DefaultRouter()
router.register(r'calendar', CalendarEntryViewSet, basename='calendar')
router.register(r'availability', AvailabilityReportViewSet, basename='availability')

urlpatterns = [
    # Authentication (User DTO Process)
    path('', HomeView.as_view(), name='home'),

    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/login/', UserLoginView.as_view(), name='login'),
    path('auth/logout/', UserLogoutView.as_view(), name='logout'),

    # Profile View
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('', include(router.urls)),
    path('', include(router.urls)),
    # Calendar and Reporting endpoints will be added here later...
]