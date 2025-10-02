import pytest
from datetime import datetime, timedelta, date
from django.contrib.auth.models import User
from django.utils import timezone
from  planningAgent.models import *
from planningAgent.services import *

# Mark this file to use the Django database for model creation
pytestmark = pytest.mark.django_db

@pytest.fixture
def setup_user_and_profile():
    """Fixture to create a User and their Profile."""
    user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
    profile = UserProfile.objects.create(user=user, first_name='Test', last_name='User')
    return profile

def create_entry(profile, category, start, end):
    """Helper to create a timezone-aware CalendarEntry."""
    return CalendarEntry.objects.create(
        user_profile=profile,
        category=category,
        title="Test Event",
        start_time=timezone.make_aware(start),
        end_time=timezone.make_aware(end)
    )

def test_availability_service_empty_calendar(setup_user_and_profile):
    """Test the service when the calendar is completely empty."""
    profile = setup_user_and_profile
    service = AvailabilityService(user_profile=profile)

    # Use a fixed Monday date for testing
    test_date = date(2025, 10, 6) # This is a Monday

    report = service.calculate_availability_for_week(test_date)

    assert report.total_available_hours == 168.0 # 7 days * 24 hours
    assert report.availability_ratio == 1.0
    assert report.hourly_details.filter(is_available=False).count() == 0

def test_availability_service_full_day_event(setup_user_and_profile):
    """Test an event that spans exactly one full 24-hour day."""
    profile = setup_user_and_profile

    # Event on Tuesday, Oct 7, 2025 (Day 1) from midnight to midnight
    start = datetime(2025, 10, 7, 0, 0)
    end = datetime(2025, 10, 8, 0, 0)
    create_entry(profile, EventCategory.WORK, start, end)

    test_date = date(2025, 10, 6) # Monday of the week

    service = AvailabilityService(user_profile=profile)
    report = service.calculate_availability_for_week(test_date)

    # 168 total hours - 24 busy hours = 144 available hours
    assert report.total_available_hours == 144.0

    # Check that the 24 hours of Tuesday (day_of_week=1) are busy
    busy_hours = report.hourly_details.filter(is_available=False).count()
    assert busy_hours == 24

    # Check a specific busy hour (Tuesday @ 10:00)
    assert not report.hourly_details.get(day_of_week=1, hour_of_day=10).is_available

def test_availability_service_partial_hour_event(setup_user_and_profile):
    """Test an event that is less than a full hour or spans partial hours."""
    profile = setup_user_and_profile

    # Event on Monday, Oct 6 (Day 0), from 10:30 to 11:30
    # This should mark BOTH the 10:00-11:00 slot and the 11:00-12:00 slot as BUSY.
    start = datetime(2025, 10, 6, 10, 30)
    end = datetime(2025, 10, 6, 11, 30)
    create_entry(profile, EventCategory.MEETING, start, end)

    test_date = date(2025, 10, 6)
    service = AvailabilityService(user_profile=profile)
    report = service.calculate_availability_for_week(test_date)

    # 10:xx slot is busy, 11:xx slot is busy. Total 2 hours busy.
    assert report.total_available_hours == 166.0
    assert report.hourly_details.filter(is_available=False).count() == 2

    # Check specific hours
    assert not report.hourly_details.get(day_of_week=0, hour_of_day=10).is_available
    assert not report.hourly_details.get(day_of_week=0, hour_of_day=11).is_available
    assert report.hourly_details.get(day_of_week=0, hour_of_day=9).is_available # Check adjacent hour is free