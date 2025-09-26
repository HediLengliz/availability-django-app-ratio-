# planning/services.py
from datetime import timedelta, date, datetime
from django.db import transaction
from django.utils import timezone
from .models import AvailabilityReport, AvailabilityHourlyDetail, UserProfile, CalendarEntry
import io
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from django.conf import settings
class AvailabilityService:
    """
    The 'AI Agent or function algorithms' responsible for calculating availability
    and generating the AvailabilityReport.
    """

    def __init__(self, user_profile: UserProfile):
        self.user_profile = user_profile

    def calculate_availability_for_week(self, target_date: date) -> AvailabilityReport:
        """
        Calculates availability for the entire week containing the target_date.

        The calculation is robust: it iterates through all 168 hours (7 days * 24 hours)
        and checks each hour slot against all user events.
        """

        # 1. Determine the Start of the Week (Monday)
        # Note: Monday=0, Sunday=6
        start_week = target_date - timedelta(days=target_date.weekday())
        end_week = start_week + timedelta(days=6)

        # Ensure we are working with timezone-aware datetimes
        start_dt = timezone.make_aware(datetime.combine(start_week, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(end_week, datetime.max.time()))

        # 2. Fetch relevant calendar entries
        entries = CalendarEntry.objects.filter(
            user_profile=self.user_profile,
            start_time__lte=end_dt,
            end_time__gte=start_dt
        ).order_by('start_time')

        # 3. Initialize Availability Grid
        # availability_grid[day_of_week][hour_of_day] = is_available (Boolean)
        availability_grid = [[True] * 24 for _ in range(7)]
        total_busy_hours = 0.0

        # 4. Populate the Grid with Busy Slots
        for entry in entries:
            # We iterate through the time range of the entry
            current_time = entry.start_time

            # Use min() to cap iteration at the end of the analysis week
            # and max() to start at the beginning of the analysis week
            while current_time < entry.end_time and current_time < end_dt:
                if current_time >= start_dt:
                    # Calculate day of week (0=Mon) and hour of day (0-23)
                    day_index = current_time.weekday()
                    hour_index = current_time.hour

                    # Check if this hourly slot is currently marked as available
                    if availability_grid[day_index][hour_index]:
                        availability_grid[day_index][hour_index] = False
                        total_busy_hours += 1.0

                current_time += timedelta(hours=1)

        # 5. Save the Report and Details atomically
        with transaction.atomic():
            # Calculate Summary
            total_hours_in_week = 7 * 24 # 168 hours
            total_available_hours = total_hours_in_week - total_busy_hours
            availability_ratio = total_available_hours / total_hours_in_week if total_hours_in_week > 0 else 0.0

            # Create the main report
            report = AvailabilityReport.objects.create(
                user_profile=self.user_profile,
                start_week=start_week,
                end_week=end_week,
                total_available_hours=total_available_hours,
                availability_ratio=availability_ratio
            )

            # Create the granular details
            details_to_create = []
            for day in range(7):
                for hour in range(24):
                    is_available = availability_grid[day][hour]
                    details_to_create.append(AvailabilityHourlyDetail(
                        report=report,
                        day_of_week=day,
                        hour_of_day=hour,
                        is_available=is_available
                    ))

            AvailabilityHourlyDetail.objects.bulk_create(details_to_create)

            return report
class ExportService:
    """
    Service responsible for generating and returning CSV and PDF files
    for the AvailabilityReport.
    """

    def __init__(self, report: AvailabilityReport):
        self.report = report

    def _get_report_data(self):
        """Helper function to format report data into a list of lists (CSV/Table format)."""
        data = []
        # Header row
        data.append(["Day", "Hour (24h)", "Availability Status"])

        # Detail rows
        # Mapping for better readability (0=Monday, 6=Sunday)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        details = self.report.hourly_details.all()

        for detail in details:
            day = day_names[detail.day_of_week]
            hour_range = f"{detail.hour_of_day:02d}:00 - {detail.hour_of_day+1:02d}:00"
            status = "Available" if detail.is_available else "Busy"
            data.append([day, hour_range, status])

        return data

    def generate_csv(self) -> bytes:
        """Generates the report data as a CSV byte stream."""
        # Use io.StringIO for text stream and then encode to bytes
        output = io.StringIO()
        writer = csv.writer(output)

        # Add summary metadata first
        writer.writerow(["REPORT SUMMARY", ""])
        writer.writerow(["User", self.report.user_profile.user.username])
        writer.writerow(["Week Start", str(self.report.start_week)])
        writer.writerow(["Total Available Hours", str(self.report.total_available_hours)])
        writer.writerow(["Availability Ratio", f"{self.report.availability_ratio:.3f}"])
        writer.writerow([])

        # Add detail rows
        for row in self._get_report_data():
            writer.writerow(row)

        return output.getvalue().encode('utf-8')

    def generate_pdf(self) -> bytes:
        """Generates the report data as a PDF byte stream using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        story = []

        # 1. Title and Summary
        title = f"Availability Report for {self.report.user_profile.user.username}"
        story.append(Paragraph(title, styles['h1']))
        story.append(Spacer(1, 12))

        summary_text = f"Week of {self.report.start_week}. Total Available Hours: **{self.report.total_available_hours}** / {self.report.total_hours} (Ratio: **{self.report.availability_ratio:.3f}**)"
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 24))

        # 2. Hourly Details Table
        table_data = self._get_report_data()
        table = Table(table_data)

        # Apply Table Style
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(Paragraph("Hourly Availability Details:", styles['h2']))
        story.append(Spacer(1, 6))
        story.append(table)

        # 3. Build the document
        doc.build(story)

        # Rewind buffer and return bytes
        buffer.seek(0)
        return buffer.read()