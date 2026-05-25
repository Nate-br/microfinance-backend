from django.urls import path
from .views import (
    NotificationListView, NotificationMarkReadView, NotificationMarkAllReadView,
    AuditLogListView, PaymentRecordListView, PaymentRecordCreateView
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification_list'),
    path('<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    path('audit-logs/', AuditLogListView.as_view(), name='audit_log_list'),
    path('payments/', PaymentRecordListView.as_view(), name='payment_record_list'),
    path('payments/create/', PaymentRecordCreateView.as_view(), name='payment_record_create'),
]