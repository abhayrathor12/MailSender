from django.db import models

class EmailTrack(models.Model):

    tracking_id = models.CharField(max_length=200, unique=True)
    email = models.EmailField()

    sent_at = models.DateTimeField(auto_now_add=True)

    opened = models.BooleanField(default=False)
    opened_at = models.DateTimeField(null=True, blank=True)

    clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)

    user_agent = models.TextField(null=True, blank=True)
    ip_address = models.CharField(max_length=100, null=True, blank=True)

    open_type = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.email