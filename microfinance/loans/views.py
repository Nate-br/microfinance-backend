from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import uuid
from .models import Loan, LoanRepayment, LoanApproval
from .serializers import (
    LoanSerializer, LoanCreateSerializer, LoanApprovalSerializer,
    LoanRepaymentSerializer, RepaymentCreateSerializer
)


class LoanApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LoanCreateSerializer(data=request.data)
        if serializer.is_valid():
            interest_rate = serializer.validated_data.get('interest_rate')
            if not interest_rate:
                interest_rate = getattr(settings, 'DEFAULT_INTEREST_RATE', 0.05)

            with transaction.atomic():
                loan = Loan.objects.create(
                    user=request.user,
                    loan_type=serializer.validated_data['loan_type'],
                    amount=serializer.validated_data['amount'],
                    interest_rate=interest_rate,
                    purpose=serializer.validated_data['purpose'],
                    term_months=serializer.validated_data['term_months'],
                    status='pending'
                )
                loan.calculate_interest()
                loan.save()

                due_date = timezone.now().date() + timedelta(days=30 * loan.term_months)
                loan.due_date = due_date
                loan.save()

                for i in range(1, loan.term_months + 1):
                    due = timezone.now().date() + timedelta(days=30 * i)
                    LoanRepayment.objects.create(
                        loan=loan,
                        installment_number=i,
                        amount=loan.monthly_payment,
                        principal=loan.amount / loan.term_months,
                        interest=loan.interest_amount / loan.term_months,
                        balance_before=loan.total_amount - (loan.monthly_payment * (i - 1)),
                        balance_after=loan.total_amount - (loan.monthly_payment * i),
                        due_date=due,
                        status='pending'
                    )

            return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyLoansView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loans = Loan.objects.filter(user=request.user)
        status_filter = request.query_params.get('status')
        if status_filter:
            loans = loans.filter(status=status_filter)
        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data)


class LoanDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer


class LoanApprovalListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        loans = Loan.objects.filter(status='pending')
        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data)


class LoanApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        try:
            loan = Loan.objects.get(pk=pk, status='pending')
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found or already processed'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        notes = request.data.get('notes', '')

        if action not in ['approve', 'reject']:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            loan.status = 'approved' if action == 'approve' else 'rejected'
            loan.approved_by = request.user
            loan.approved_at = timezone.now()
            loan.save()

            LoanApproval.objects.create(
                loan=loan,
                action=action,
                reviewed_by=request.user,
                notes=notes
            )

        return Response(LoanSerializer(loan).data)


class LoanDisbursementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        try:
            loan = Loan.objects.get(pk=pk, status='approved')
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found or not approved'}, status=status.HTTP_404_NOT_FOUND)

        from wallet.models import Wallet
        with transaction.atomic():
            wallet, _ = Wallet.objects.get_or_create(user=loan.user)
            wallet = Wallet.objects.select_for_update().get(user=loan.user)

            wallet.balance += loan.amount
            wallet.available_balance += loan.amount
            wallet.save()

            loan.status = 'active'
            loan.disbursed_at = timezone.now()
            loan.save()

        return Response(LoanSerializer(loan).data)


class RepaymentScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        loan = Loan.objects.get(pk=pk, user=request.user)
        repayments = loan.repayments.all()
        serializer = LoanRepaymentSerializer(repayments, many=True)
        return Response(serializer.data)


class MakeRepaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = RepaymentCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                loan = Loan.objects.get(pk=pk, user=request.user)
            except Loan.DoesNotExist:
                return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

            if loan.status not in ['active', 'disbursed']:
                return Response({'error': 'Loan not active'}, status=status.HTTP_400_BAD_REQUEST)

            amount = serializer.validated_data['amount']

            with transaction.atomic():
                from wallet.models import Wallet
                wallet = Wallet.objects.select_for_update().get(user=request.user)

                if wallet.available_balance < amount:
                    return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

                pending_repayments = loan.repayments.filter(status='pending').order_by('installment_number')

                remaining_amount = amount
                total_paid = 0

                for repayment in pending_repayments:
                    if remaining_amount <= 0:
                        break

                    payment = min(remaining_amount, repayment.amount + repayment.penalty)
                    total_paid += payment
                    remaining_amount -= payment

                    repayment.paid_date = timezone.now().date()
                    repayment.payment_method = serializer.validated_data['payment_method']
                    repayment.reference_number = f"REP-{uuid.uuid4().hex[:12].upper()}"
                    repayment.balance_before = loan.total_amount - (loan.monthly_payment * (repayment.installment_number - 1))
                    remaining_balance = loan.total_amount - (loan.monthly_payment * repayment.installment_number)
                    repayment.balance_after = max(0, remaining_balance)

                    if payment >= repayment.amount + repayment.penalty:
                        repayment.status = 'paid'
                        if repayment.due_date < timezone.now().date():
                            repayment.status = 'late'
                    else:
                        repayment.status = 'partial'

                    repayment.save()

                wallet.balance -= total_paid
                wallet.available_balance -= total_paid
                wallet.save()

                all_paid = not loan.repayments.filter(status='pending').exists()
                if all_paid:
                    loan.status = 'paid_off'
                    loan.save()

            return Response({'message': 'Payment successful', 'amount_paid': total_paid})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoanHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loans = Loan.objects.filter(user=request.user).order_by('-created_at')[:50]
        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data)


class AllLoansView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        loans = Loan.objects.all()
        status_filter = request.query_params.get('status')
        if status_filter:
            loans = loans.filter(status=status_filter)

        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data)