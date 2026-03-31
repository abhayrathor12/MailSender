from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from .models import EmailTrack
import base64





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

    print("EMAIL OPENED:", tracking_id)
    print("User-Agent:", user_agent)
    print("IP:", ip)

    try:
        obj = EmailTrack.objects.get(tracking_id=tracking_id)

        obj.opened = True

        if not obj.opened_at:
            obj.opened_at = timezone.now()

        # Gmail proxy detection
        if "GoogleImageProxy" in user_agent:
            obj.open_type = "gmail_proxy"
        else:
            obj.open_type = "direct"

        obj.ip_address = ip
        obj.user_agent = user_agent

        obj.save()

    except EmailTrack.DoesNotExist:
        pass

    return HttpResponse(get_pixel(), content_type="image/gif")


# 🔸 Track Link Click
def track_click(request, tracking_id):

    user_agent = request.META.get("HTTP_USER_AGENT", "")
    ip = get_client_ip(request)

    redirect_url = request.GET.get("url", "https://google.com")

    print("LINK CLICKED:", tracking_id)
    print("User-Agent:", user_agent)
    print("IP:", ip)

    try:
        obj = EmailTrack.objects.get(tracking_id=tracking_id)

        obj.clicked = True

        if not obj.clicked_at:
            obj.clicked_at = timezone.now()

        # detect gmail proxy
        if "GoogleImageProxy" in user_agent:
            obj.open_type = "gmail_proxy"
        else:
            obj.open_type = "direct"

        obj.ip_address = ip
        obj.user_agent = user_agent

        obj.save()

    except EmailTrack.DoesNotExist:
        pass

    return redirect(redirect_url)


import uuid

def create_tracking(email):
    tracking_id = str(uuid.uuid4())

    EmailTrack.objects.create(
        tracking_id=tracking_id,
        email=email
    )

    return tracking_id
   
   
   
    # tracker/views.py

from django.http import JsonResponse
from .models import EmailTrack

def get_data(request):
    data = list(EmailTrack.objects.values())
    return JsonResponse(data, safe=False)

from django.shortcuts import render
from .models import EmailTrack

def dashboard(request):
    data = EmailTrack.objects.all().order_by('-sent_at')
    return render(request, 'dashboard.html', {'data': data})


from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
import uuid

BASE_URL = "https://sendermailing.pythonanywhere.com"

def send_tracking_email(to_email, tracking_id):

    subject = "Test Tracking"

    html_content = f"""
<html>
<body>

<p>Hello,</p>
<p>Check this out:</p>

<a href="{BASE_URL}/track/click/{tracking_id}?url=https://google.com" target="_blank">
    Open Link
</a>

<p style="font-size:0;">
<img src="{BASE_URL}/track/open/{tracking_id}/?t={uuid.uuid4()}"
     width="1"
     height="1"
     style="display:none;">
</p>

<div style="background-image:url('{BASE_URL}/track/open/{tracking_id}/?bg={uuid.uuid4()}'); width:1px; height:1px;">
</div>

</body>
</html>
"""

    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject,
        text_content,
        "your_email@gmail.com",
        [to_email]
    )

    email.attach_alternative(html_content, "text/html")
    email.send()
    
from django.http import HttpResponse

def send_email_view(request):
    email = request.GET.get('email')

    if not email:
        return HttpResponse("Please provide email ?email=test@gmail.com")

    # create tracking id
    tracking_id = create_tracking(email)

    # send email
    send_tracking_email(email, tracking_id)

    return HttpResponse(f"Email sent to {email}")

from django.shortcuts import render
from django.http import HttpResponse


def send_email_view(request):

    if request.method == "POST":

        email = request.POST.get("email")

        if not email:
            return HttpResponse("Email required")

        # create tracking id
        tracking_id = create_tracking(email)

        # send email
        send_tracking_email(email, tracking_id)

        return HttpResponse(f"Email sent to {email}")

    return render(request, "send_email.html")