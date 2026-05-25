from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
import uuid
from .models import Wallet, SavingsTransaction, InterestRule, PenaltyRule
from .serializers import (
    WalletSerializer, SavingsTransactionSerializer,
    DepositSerializer, WithdrawSerializer,
    InterestRuleSerializer, PenaltyRuleSerializer
)


class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


class DepositView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                amount = serializer.validated_data['amount']

                transaction_obj = SavingsTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='deposit',
                    payment_method=serializer.validated_data['payment_method'],
                    amount=amount,
                    balance_before=wallet.balance,
                    balance_after=wallet.balance + amount,
                    reference_number=f"DEP-{uuid.uuid4().hex[:12].upper()}",
                    description=serializer.validated_data.get('description', ''),
                    status='completed'
                )

                wallet.balance += amount
                wallet.available_balance += amount
                wallet.total_saved += amount
                wallet.save()

            return Response(
                SavingsTransactionSerializer(transaction_obj).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WithdrawSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                amount = serializer.validated_data['amount']

                if wallet.available_balance < amount:
                    return Response(
                        {'error': 'Insufficient balance'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                transaction_obj = SavingsTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='withdrawal',
                    payment_method=serializer.validated_data['payment_method'],
                    amount=amount,
                    balance_before=wallet.balance,
                    balance_after=wallet.balance - amount,
                    reference_number=f"WTH-{uuid.uuid4().hex[:12].upper()}",
                    description=serializer.validated_data.get('description', ''),
                    status='completed'
                )

                wallet.balance -= amount
                wallet.available_balance -= amount
                wallet.save()

            return Response(
                SavingsTransactionSerializer(transaction_obj).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = Wallet.objects.get(user=request.user)
        transactions = SavingsTransaction.objects.filter(wallet=wallet)

        transaction_type = request.query_params.get('type')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)

        status_filter = request.query_params.get('status')
        if status_filter:
            transactions = transactions.filter(status=status_filter)

        date_from = request.query_params.get('date_from')
        if date_from:
            transactions = transactions.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            transactions = transactions.filter(created_at__date__lte=date_to)

        transactions = transactions[:50]
        serializer = SavingsTransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class InterestRuleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rules = InterestRule.objects.filter(is_active=True)
        serializer = InterestRuleSerializer(rules, many=True)
        return Response(serializer.data)


class PenaltyRuleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rules = PenaltyRule.objects.filter(is_active=True)
        serializer = PenaltyRuleSerializer(rules, many=True)
        return Response(serializer.data)


class ManualTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        transaction_type = request.data.get('transaction_type')
        amount = request.data.get('amount')
        user_id = request.data.get('user_id')
        description = request.data.get('description', '')

        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        if not all([transaction_type, amount, user_id]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            wallet, _ = Wallet.objects.get_or_create(user=target_user)
            wallet = Wallet.objects.select_for_update().get(user=target_user)

            if transaction_type == 'deposit':
                wallet.balance += amount
                wallet.available_balance += amount
                wallet.total_saved += amount
            elif transaction_type == 'withdrawal':
                if wallet.available_balance < amount:
                    return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
                wallet.balance -= amount
                wallet.available_balance -= amount
            else:
                return Response({'error': 'Invalid transaction type'}, status=status.HTTP_400_BAD_REQUEST)

            wallet.save()

            transaction_obj = SavingsTransaction.objects.create(
                wallet=wallet,
                transaction_type=transaction_type,
                payment_method='cash',
                amount=amount,
                balance_before=wallet.balance - (amount if transaction_type == 'deposit' else -amount),
                balance_after=wallet.balance,
                reference_number=f"MAN-{uuid.uuid4().hex[:12].upper()}",
                description=f"Manual transaction by {request.user.username}: {description}",
                status='completed',
                processed_by=request.user
            )

        return Response(SavingsTransactionSerializer(transaction_obj).data, status=status.HTTP_201_CREATED)