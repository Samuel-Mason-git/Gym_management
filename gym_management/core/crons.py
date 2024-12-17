from django.utils.timezone import now
import time

def auto_exit_cron_job():
    """Marks overdue visits as complete."""
    from .models import Visit

    while True:
        print("Running auto_exit_cron_job...")  # For debugging; remove in production
        # Fetch all visits that haven't exited and are overdue
        overdue_visits = Visit.objects.filter(exit_time__isnull=True, has_exit=False)
        for visit in overdue_visits:
            elapsed_time = now() - visit.entry_time
            if elapsed_time > visit.default_exit_threshold:
                # Mark visit as completed
                visit.exit_time = visit.entry_time + visit.default_exit_duration
                visit.has_exit = True
                visit.save()
                print("Updated Visit Exit")
        time.sleep(300)  # Wait for 5 minutes (300 seconds) before running again