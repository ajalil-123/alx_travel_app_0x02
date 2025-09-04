from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_payment_success_email(user_email, booking_reference):
    send_mail(
        "Payment Confirmation",
        f"Your payment for booking {booking_reference} was successful.",
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )


from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_booking_confirmation_email(user_email, booking_id, user_name=None, listing_name=None, start_date=None, end_date=None):
    """Send booking confirmation email"""

    subject = "Booking Confirmation"
    message = f"""
Dear {user_name or 'Valued Customer'},

Thank you for your booking with ALX Travel App!

Booking Details:
- Booking ID: {booking_id}
- Property: {listing_name or 'N/A'}
- Check-in: {start_date}
- Check-out: {end_date}

We look forward to hosting you!

Best regards,
ALX Travel App Team
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )
