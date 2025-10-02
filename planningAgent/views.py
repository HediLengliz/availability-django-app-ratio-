# planning/views.py
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.decorators import action
from .services import AvailabilityService, ExportService
from .models import AvailabilityReport
from .serializers import AvailabilityReportSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import CalendarEntry
from .serializers import CalendarEntrySerializer
from datetime import datetime
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
class UserRegistrationView(APIView):
    """
    Handles POST requests for new user registration (Sign Up).
    """
    permission_classes = [AllowAny]
    @swagger_auto_schema(request_body=UserRegistrationSerializer)
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # The .create() method handles User and UserProfile creation
            user = serializer.save()
            # Respond with user data (excluding password)
            return Response({
                "message": "User created successfully. Please log in.",
                "id": user.id,
                "username": user.username,
                "email": user.email
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    """
    Handles POST requests for local user login.
    Uses Django's session authentication to log the user in.
    """
    permission_classes = [AllowAny]
    @swagger_auto_schema(request_body=UserRegistrationSerializer)
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            # Authenticate the user against Django's built-in system
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Log the user in to establish a session (important for DRF SessionAuth)
                login(request, user)
                return Response({"message": "Login successful", "username": user.username})
            else:
                return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLogoutView(APIView):
    """
    Handles user logout and session termination.
    """
    permission_classes = [IsAuthenticated] # Only authenticated users can log out
    @swagger_auto_schema(request_body=UserRegistrationSerializer)
    def post(self, request):
        logout(request)
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)

class UserProfileView(APIView):
    """
    Returns the current authenticated user's profile data.
    """
    permission_classes = [IsAuthenticated]
    def get(self, request):
        profile = request.user.profile # Access the UserProfile via the related_name='profile'
        serializer = UserProfileSerializer(profile)
        return Response({
            "username": request.user.username,
            "email": request.user.email,
            "profile": serializer.data
        }, status=status.HTTP_200_OK)
class HomeView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({"message": "Welcome to Planning Agent API"})
class CalendarEntryViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD operations for CalendarEntry objects.
    - List (GET /api/v1/calendar/)
    - Retrieve (GET /api/v1/calendar/{id}/)
    - Create (POST /api/v1/calendar/)
    - Update/Partial Update (PUT/PATCH /api/v1/calendar/{id}/)
    - Destroy (DELETE /api/v1/calendar/{id}/)
    """
    serializer_class = CalendarEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Ensures users can only see their own calendar entries.
        """
        # Access the UserProfile linked to the authenticated user
        user_profile = self.request.user.profile
        return CalendarEntry.objects.filter(user_profile=user_profile)

    def perform_create(self, serializer):
        """
        Links the new CalendarEntry to the current authenticated UserProfile.
        """
        # Get the UserProfile from the request's authenticated user
        user_profile = self.request.user.profile
        serializer.save(user_profile=user_profile)
class AvailabilityReportViewSet(mixins.ListModelMixin,
                                mixins.RetrieveModelMixin,
                                viewsets.GenericViewSet):
    serializer_class = AvailabilityReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_profile = self.request.user.profile
        return AvailabilityReport.objects.filter(user_profile=user_profile).order_by('-start_week')

    @action(detail=False, methods=['post'], url_path='calculate')
    def calculate_report(self, request):
        target_date_str = request.data.get('date')
        if not target_date_str:
            return Response({"detail": "Missing 'date' parameter (YYYY-MM-DD) in request body."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            service = AvailabilityService(user_profile=request.user.profile)
            report = service.calculate_availability_for_week(target_date)
            serializer = self.get_serializer(report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(f"Error during availability calculation: {e}")
            return Response({"detail": "An internal error occurred during calculation."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='export-csv')
    def export_csv(self, request, pk=None):
        try:
            report = self.get_object()
        except NotFound:
            return Response({"detail": "Report not found or not authorized."}, status=status.HTTP_404_NOT_FOUND)
        export_service = ExportService(report=report)
        csv_data = export_service.generate_csv()
        filename = f"availability_report_{report.start_week}_{report.id}.csv"
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
        return response

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        try:
            report = self.get_object()
        except NotFound:
            return Response({"detail": "Report not found or not authorized."}, status=status.HTTP_404_NOT_FOUND)
        export_service = ExportService(report=report)
        pdf_data = export_service.generate_pdf()
        filename = f"availability_report_{report.start_week}_{report.id}.pdf"
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
        return response