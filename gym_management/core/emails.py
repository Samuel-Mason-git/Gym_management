from django.core.mail import EmailMessage
from django.conf import settings

def send_email(subject, body, recipient_list, gym=None):
    """
    Sends an email with the option to use a gym's custom email domain.

    Args:
        subject (str): The email subject.
        body (str): The email body (HTML or plain text).
        recipient_list (list): List of recipient email addresses.
        gym (Gym, optional): Gym object to use its custom email domain.
    """
    email_from = f"{gym.name if gym else 'System'} <{gym.email_domain if gym and gym.email_domain else settings.DEFAULT_FROM_EMAIL}>"
    email = EmailMessage(subject, body, email_from, recipient_list)
    email.content_subtype = 'html' 
    email.send()