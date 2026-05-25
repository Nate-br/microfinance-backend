from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from wallet.models import Wallet, SavingsTransaction
from loans.models import Loan, LoanRepayment
from accounts.models import User


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.now().date()
        month_start = today.replace(day=1)

        total_users = User.objects.filter(role='customer').count()
        active_loans = Loan.objects.filter(status='active').count()
        pending_loans = Loan.objects.filter(status='pending').count()

        total_wallet = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0
        total_savings = Wallet.objects.aggregate(total=Sum('total_saved'))['total'] or 0

        monthly_deposits = SavingsTransaction.objects.filter(
            transaction_type='deposit',
            created_at__date__gte=month_start,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        monthly_withdrawals = SavingsTransaction.objects.filter(
            transaction_type='withdrawal',
            created_at__date__gte=month_start,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_disbursed = Loan.objects.filter(
            status__in=['active', 'disbursed', 'paid_off']
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_collected = LoanRepayment.objects.filter(
            status__in=['paid', 'late']
        ).aggregate(total=Sum('amount'))['total'] or 0

        overdue_loans = Loan.objects.filter(
            status__in=['active', 'disbursed'],
            due_date__lt=today
        ).count()

        return Response({
            'total_users': total_users,
            'active_loans': active_loans,
            'pending_loans': pending_loans,
            'total_wallet': float(total_wallet),
            'total_savings': float(total_savings),
            'monthly_deposits': float(monthly_deposits),
            'monthly_withdrawals': float(monthly_withdrawals),
            'total_disbursed': float(total_disbursed),
            'total_collected': float(total_collected),
            'overdue_loans': overdue_loans,
        })


class CustomerStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = Wallet.objects.get(user=request.user)

        deposits = SavingsTransaction.objects.filter(
            wallet=wallet,
            transaction_type='deposit',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        withdrawals = SavingsTransaction.objects.filter(
            wallet=wallet,
            transaction_type='withdrawal',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        active_loans = Loan.objects.filter(
            user=request.user,
            status__in=['active', 'disbursed']
        ).count()

        pending_loans = Loan.objects.filter(
            user=request.user,
            status='pending'
        ).count()

        return Response({
            'balance': float(wallet.balance),
            'available_balance': float(wallet.available_balance),
            'total_saved': float(wallet.total_saved),
            'total_interest_earned': float(wallet.total_interest_earned),
            'total_deposits': float(deposits),
            'total_withdrawals': float(withdrawals),
            'active_loans': active_loans,
            'pending_loans': pending_loans,
        })


class TransactionReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        transactions = SavingsTransaction.objects.filter(status='completed')

        if date_from:
            transactions = transactions.filter(created_at__date__gte=date_from)
        if date_to:
            transactions = transactions.filter(created_at__date__lte=date_to)

        total_deposits = transactions.filter(transaction_type='deposit').aggregate(total=Sum('amount'))['total'] or 0
        total_withdrawals = transactions.filter(transaction_type='withdrawal').aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'total_deposits': float(total_deposits),
            'total_withdrawals': float(total_withdrawals),
            'net_change': float(total_deposits - total_withdrawals),
            'transaction_count': transactions.count(),
        })


class LoanReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        loans = Loan.objects.all()

        status_summary = {}
        for status_code, status_name in Loan.STATUS_CHOICES:
            count = loans.filter(status=status_code).count()
            total = loans.filter(status=status_code).aggregate(total=Sum('amount'))['total'] or 0
            status_summary[status_code] = {
                'count': count,
                'total': float(total)
            }

        return Response(status_summary)


class ExportReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        report_type = request.query_params.get('type', 'transactions')

        if report_type == 'transactions':
            transactions = SavingsTransaction.objects.filter(status='completed')[:1000]
            data = [
                {
                    'id': t.id,
                    'type': t.transaction_type,
                    'amount': float(t.amount),
                    'balance_after': float(t.balance_after),
                    'reference': t.reference_number,
                    'date': t.created_at.isoformat(),
                }
                for t in transactions
            ]
        elif report_type == 'loans':
            loans = Loan.objects.all()[:1000]
            data = [
                {
                    'id': l.id,
                    'user': l.user.username,
                    'amount': float(l.amount),
                    'status': l.status,
                    'term_months': l.term_months,
                    'due_date': l.due_date.isoformat(),
                }
                for l in loans
            ]
        else:
            data = []

        return Response({'data': data, 'count': len(data)})