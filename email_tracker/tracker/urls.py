from django.urls import path
from . import views

urlpatterns = [
    path('track/open/<str:tracking_id>/', views.track_open),
    path('track/click/<str:tracking_id>/', views.track_click),
    path('api/data/', views.get_data),
    path('', views.dashboard,name='dashboard'),
    path('send-email/', views.send_email_view),
    path("send/", views.send_email_view, name="send"),
    path("contacts/", views.contacts_page, name="contacts"),

    path("groups/", views.groups_page, name="groups"),

    path("schedule/", views.schedule_page, name="schedule"),

    path("schedule/send/<int:group_id>/",
         views.start_schedule,
         name="start_schedule"),
    path("schedule/status/", views.sending_status, name="sending_status"),
]