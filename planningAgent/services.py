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
from datetime import timedelta, date, datetime
from django.db import transaction
from django.utils import timezone
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

        # Ensure we are working with timezone-aware datetimes
        start_dt = timezone.make_aware(datetime.combine(start_week, datetime.min.time()))

        # End time should be the *very end* of Sunday (7 days later)
        end_dt = start_dt + timedelta(days=7)

        # 2. Fetch relevant calendar entries
        # Events that start before the week ends AND end after the week starts
        entries = CalendarEntry.objects.filter(
            user_profile=self.user_profile,
            start_time__lt=end_dt,
            end_time__gt=start_dt
        ).order_by('start_time')

        # 3. Initialize Availability Grid
        # availability_grid[day_of_week][hour_of_day] = is_available (Boolean)
        availability_grid = [[True] * 24 for _ in range(7)]
        total_busy_hours = 0.0

        # 4. Iterate through every hour of the week and check for overlap
        current_slot_start = start_dt

        while current_slot_start < end_dt:
            current_slot_end = current_slot_start + timedelta(hours=1)

            # Calculate indices for the grid
            day_index = current_slot_start.weekday()
            hour_index = current_slot_start.hour

            # Check if this slot has already been marked busy (shouldn't happen with this loop structure,
            # but good practice if using a different calculation method later)
            if availability_grid[day_index][hour_index]:

                # Check for overlap: Is any event active during the slot [current_slot_start, current_slot_end)?
                is_busy = False
                for entry in entries:
                    # Overlap condition: (A_start < B_end) AND (A_end > B_start)
                    # A = Event time, B = Slot time
                    if entry.start_time < current_slot_end and entry.end_time > current_slot_start:
                        is_busy = True
                        break # Found one overlapping event, slot is busy.

                if is_busy:
                    availability_grid[day_index][hour_index] = False
                    total_busy_hours += 1.0

            # Move to the next hourly slot
            current_slot_start = current_slot_end

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
                # The week ends on the *day* before the start_dt + 7 days
                end_week=start_dt.date() + timedelta(days=6),
                total_hours=total_hours_in_week,
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