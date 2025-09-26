from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# --- Enums (using Django's CharField choices) ---
class EventCategory(models.TextChoices):
    MEETING = 'MEET', _('Meeting')
    WORK = 'WORK', _('Work')
    GYM = 'GYM', _('Gym/Exercise')
    MEAL = 'MEAL', _('Meal')
    SLEEP = 'SLEEP', _('Sleep')
    VACATION = 'VAC', _('Vacation/Time Off')
    OTHER = 'OTHR', _('Other')


# --- 1. User/Profile Models ---
class UserProfile(models.Model):
    """Application-specific profile data linked to a User."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="The core Django User object."
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    telephone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


class GoogleAccount(models.Model):
    """Model to store Google SSO details."""
    user_profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='google_account'
    )
    google_id = models.CharField(max_length=255, unique=True, help_text="Unique Google identifier.")
    access_token = models.TextField(blank=True, help_text="OAuth access token.")
    refresh_token = models.TextField(blank=True, help_text="OAuth refresh token.")

    def __str__(self):
        return f"Google SSO for {self.user_profile.user.username}"


# --- 2. Calendar/Entry Models ---
class CalendarEntry(models.Model):
    """The raw data input by the user (meetings, sleep, etc.)."""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='calendar_entries')
    category = models.CharField(max_length=5, choices=EventCategory.choices)
    title = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        ordering = ['start_time']
        verbose_name_plural = "Calendar Entries"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title} @ {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    # You would add clean() or save() method here for validation (e.g., end_time > start_time)


# --- 3. Availability Models (The Output) ---
class AvailabilityReport(models.Model):
    """Weekly summary of the calculated availability."""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='reports')
    start_week = models.DateField(help_text="The Monday date of the week being analyzed.")
    end_week = models.DateField(help_text="The Sunday date of the week being analyzed.")
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=24 * 7) # 168 hours total
    total_available_hours = models.DecimalField(max_digits=5, decimal_places=2)
    availability_ratio = models.DecimalField(max_digits=4, decimal_places=3, help_text="Ratio (0.0 to 1.0).")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.user_profile.user.username} (Week of {self.start_week})"


class AvailabilityHourlyDetail(models.Model):
    """Granular availability status for each hour of the week."""
    report = models.ForeignKey(AvailabilityReport, on_delete=models.CASCADE, related_name='hourly_details')
    day_of_week = models.PositiveSmallIntegerField(help_text="0=Monday, 6=Sunday")
    hour_of_day = models.PositiveSmallIntegerField(help_text="0-23")
    is_available = models.BooleanField(default=False)

    class Meta:
        unique_together = ('report', 'day_of_week', 'hour_of_day')
        ordering = ['day_of_week', 'hour_of_day']

    def __str__(self):
        return f"Day {self.day_of_week} @ {self.hour_of_day}: {self.is_available}"