from rest_framework import serializers
from .models import Notification, AuditLog, PaymentRecord


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'related_object_id', 'related_object_type', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationListView(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_username', 'action', 'entity_type', 'entity_id',
            'old_values', 'new_values', 'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = fields


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = [
            'id', 'user', 'payment_type', 'method', 'amount', 'reference_number',
            'phone_number', 'bank_name', 'account_number', 'transaction_id',
            'status', 'notes', 'processed_by', 'created_at'
        ]
        read_only_fields = ['id', 'reference_number', 'processed_by', 'created_at']