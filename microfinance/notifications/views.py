from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification, AuditLog, PaymentRecord
from .serializers import NotificationSerializer, AuditLogSerializer, PaymentRecordSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        unread_only = request.query_params.get('unread')
        if unread_only == 'true':
            notifications = notifications.filter(is_read=False)
        notifications = notifications[:50]
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.is_read = True
            notification.save()
            return Response({'message': 'Marked as read'})
        except Notification.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'})


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        logs = AuditLog.objects.all()
        action_filter = request.query_params.get('action')
        if action_filter:
            logs = logs.filter(action=action_filter)

        entity_type = request.query_params.get('entity_type')
        if entity_type:
            logs = logs.filter(entity_type=entity_type)

        user_id = request.query_params.get('user_id')
        if user_id:
            logs = logs.filter(user_id=user_id)

        logs = logs[:100]
        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)


class PaymentRecordListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        records = PaymentRecord.objects.filter(user=request.user)
        if request.user.role == 'admin':
            records = PaymentRecord.objects.all()

        status_filter = request.query_params.get('status')
        if status_filter:
            records = records.filter(status=status_filter)

        payment_type = request.query_params.get('payment_type')
        if payment_type:
            records = records.filter(payment_type=payment_type)

        records = records[:50]
        serializer = PaymentRecordSerializer(records, many=True)
        return Response(serializer.data)


class PaymentRecordCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PaymentRecordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(processed_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)