from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from .models import UserProfile
from .models import CalendarEntry
from .models import AvailabilityReport, AvailabilityHourlyDetail

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for the application-specific UserProfile."""
    class Meta:
        model = UserProfile
        exclude = ('id', 'user')


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for User registration (Sign Up)."""
    telephone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    age = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name', 'telephone', 'age')
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    @transaction.atomic
    def create(self, validated_data):
        # Extract profile-related data
        profile_data = {
            'telephone': validated_data.pop('telephone', ''),
            'age': validated_data.pop('age', None)
        }
        # Create the core Django User
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        # Create the UserProfile linked to the User
        UserProfile.objects.create(user=user, **profile_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    """Serializer for handling local login credentials."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class CalendarEntrySerializer(serializers.ModelSerializer):
    """Serializer for the CalendarEntry model."""

    # Read-only field to display the category label instead of the code
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = CalendarEntry
        # user_profile is handled automatically by the view, so it's read_only
        fields = ('id', 'category', 'category_display', 'title', 'start_time', 'end_time', 'user_profile')
        read_only_fields = ('user_profile',)

    def validate(self, data):
        """Custom validation to ensure end_time is after start_time."""
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError({"end_time": "End time must occur after start time."})
        return data
class AvailabilityHourlyDetailSerializer(serializers.ModelSerializer):
    """Serializer for the granular hourly availability data."""
    class Meta:
        model = AvailabilityHourlyDetail
        exclude = ('id', 'report')


class AvailabilityReportSerializer(serializers.ModelSerializer):
    """Serializer for the weekly availability summary and its details."""
    hourly_details = AvailabilityHourlyDetailSerializer(many=True, read_only=True)

    class Meta:
        model = AvailabilityReport
        fields = (
            'id',
            'start_week',
            'end_week',
            'total_hours',
            'total_available_hours',
            'availability_ratio',
            'created_at',
            'hourly_details'
        )
        read_only_fields = fields # All fields are results, not user inputs