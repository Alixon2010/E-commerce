from os import getenv

from celery import shared_task
from django.core.mail import send_mail
from dotenv import load_dotenv

load_dotenv()
@shared_task
def send_contact_email(name, email, phone, message):
    admins = getenv("ADMINS")
    print(admins)

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


@shared_task
def send_mail_(title, message, user, emails, fail_silently):
    send_mail(
        title,
        message,
        user,
        emails,
        fail_silently=fail_silently,
    )
