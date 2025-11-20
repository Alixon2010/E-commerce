from os import getenv

from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_contact_email(name, email, phone, message):
    admins = getenv("ADMINS")

    subject = f"Message from {name}"
    body = f"""
    Name: {name}
    Email: {email}
    Phone: {phone}
    Message: {message}
    """
    send_mail(
        subject,
        body,
        None,
        [admin for admin in admins.split(",")],
        fail_silently=False,
    )
