from turtle import delay

from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from .models import EmailTrack, Contact, Group
import base64
import threading
import time
import random
import uuid


# ── Global lock: only one group can send at a time ──
_sending_lock = threading.Lock()
_is_sending = False


def get_email_status(user_agent, ip):
    ua = (user_agent or "").lower()

    if "googleimageproxy" in ua or "ggpht.com" in ua:
        return "opened"

    if ip.startswith("74.125."):
        return "opened"


def get_pixel():
    pixel = base64.b64decode(
        "R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
    )
    return pixel


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def track_open(request, tracking_id):
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    ip = get_client_ip(request)
    status = get_email_status(user_agent, ip)

    try:
        obj = EmailTrack.objects.get(tracking_id=tracking_id)
        if status == "delivered":
            obj.delivered = True
            if not obj.delivered_at:
                obj.delivered_at = timezone.now()
        if status == "opened":
            obj.opened = True
            if not obj.opened_at:
                obj.opened_at = timezone.now()
        obj.open_type = status
        obj.ip_address = ip
        obj.user_agent = user_agent
        obj.save()
    except EmailTrack.DoesNotExist:
        pass

    return HttpResponse(get_pixel(), content_type="image/gif")


def track_click(request, tracking_id):
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
    ip = get_client_ip(request)

    bot_keywords = ["google", "bot", "scanner", "curl", "python", "proofpoint"]
    if any(word in user_agent for word in bot_keywords):
        return redirect(request.GET.get("url", "https://google.com"))

    redirect_url = request.GET.get("url", "https://google.com")

    try:
        obj = EmailTrack.objects.get(tracking_id=tracking_id)
        obj.clicked = True
        if not obj.clicked_at:
            obj.clicked_at = timezone.now()
        obj.ip_address = ip
        obj.user_agent = user_agent
        obj.save()
    except EmailTrack.DoesNotExist:
        pass

    return redirect(redirect_url)


def create_tracking(email):
    tracking_id = str(uuid.uuid4())
    EmailTrack.objects.create(tracking_id=tracking_id, email=email)
    return tracking_id


def get_data(request):
    data = list(EmailTrack.objects.values())
    return JsonResponse(data, safe=False)


from django.shortcuts import render
from django.http import JsonResponse
from .models import EmailTrack


def dashboard(request):
    return render(request, "dashboard.html")


def dashboard_data(request):
    emails = EmailTrack.objects.all().order_by("-sent_at")

    data = []

    for item in emails:
        data.append({
            "email": item.email,
            "delivered": item.delivered,
            "opened": item.opened,
            "clicked": item.clicked,
            "delivered_at": item.delivered_at,
            "opened_at": item.opened_at,
            "clicked_at": item.clicked_at,
            "user_agent": item.user_agent,
            "ip_address": item.ip_address,
            "open_type": item.open_type,
        })

    return JsonResponse({"data": data})



from django.utils.html import strip_tags
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# BASE_URL = "https://0650-122-180-247-129.ngrok-free.app "


from django.conf import settings
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

BASE_URL = "https://sendermailing.pythonanywhere.com"


def send_tracking_email(to_email, tracking_id):
    subject = "Test Tracking"

    html_content = f"""
<html>
<body>
<p>Hello,</p>
<p>Check this out:</p>
<a href="{BASE_URL}/track/click/{tracking_id}?url=https://google.com" target="_blank">Open Link</a>
<p style="font-size:0;">
<img src="{BASE_URL}/track/open/{tracking_id}/?t={uuid.uuid4()}" width="1" height="1" style="display:none;">
</p>
<div style="background-image:url('{BASE_URL}/track/open/{tracking_id}/?bg={uuid.uuid4()}'); width:1px; height:1px;"></div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_HOST_USER
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls()

        server.login(
            settings.EMAIL_HOST_USER,
            settings.EMAIL_HOST_PASSWORD.replace(" ", "")
        )

        response = server.sendmail(
            settings.EMAIL_HOST_USER,
            [to_email],
            msg.as_string()
        )

        server.quit()

        if response == {}:
            obj = EmailTrack.objects.get(tracking_id=tracking_id)
            obj.delivered = True
            obj.delivered_at = timezone.now()
            obj.save()

    except Exception as e:
        print("SMTP Error:", e)
from django.shortcuts import render


def send_email_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if not email:
            return HttpResponse("Email required")
        tracking_id = create_tracking(email)
        send_tracking_email(email, tracking_id)
        return HttpResponse(f"Email sent to {email}")
    return render(request, "send_email.html")


def contacts_page(request):
    contacts = Contact.objects.all()
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        Contact.objects.create(name=name, email=email)
        return redirect("contacts")
    return render(request, "contact.html", {"contacts": contacts})


def groups_page(request):
    groups = Group.objects.all()
    contacts = Contact.objects.all()
    if request.method == "POST":
        name = request.POST.get("name")
        contact_ids = request.POST.getlist("contacts")
        group = Group.objects.create(name=name)
        group.contacts.set(contact_ids)
        return redirect("groups")
    return render(request, "groups.html", {"groups": groups, "contacts": contacts})


def schedule_page(request):
    groups = Group.objects.all()
    return render(request, "schedule.html", {"groups": groups})


def send_group_emails(group_id, group_name):
    global _is_sending
    try:
        group = Group.objects.get(id=group_id)

        for contact in group.contacts.all():
            tracking_id = create_tracking(contact.email)
            send_tracking_email(contact.email, tracking_id)

            delay = random.randint(15, 40)
            time.sleep(delay)

    finally:
        _is_sending = False


def start_schedule(request, group_id):
    global _is_sending

    with _sending_lock:
        if _is_sending:
            return JsonResponse({
                "status": "busy",
                "message": "Another group is currently sending emails. Please wait."
            }, status=409)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "Group not found."
            }, status=404)

        _is_sending = True

        # Start background thread
        thread = threading.Thread(
            target=send_group_emails,
            args=(group_id, group.name),
            daemon=True
        )
        thread.start()

    return JsonResponse({
        "status": "started",
        "message": f"Emails for group \"{group.name}\" are being sent."
    })
    
def sending_status(request):
    return JsonResponse({
        "sending": _is_sending
    })