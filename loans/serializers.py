from rest_framework import serializers
from .models import Loan, LoanRepayment, LoanApproval


class LoanSerializer(serializers.ModelSerializer):
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'user', 'loan_type', 'amount', 'interest_rate', 'interest_amount',
            'total_amount', 'status', 'purpose', 'term_months', 'monthly_payment',
            'approved_by', 'approved_by_username', 'approved_at', 'disbursed_at',
            'due_date', 'created_at'
        ]
        read_only_fields = [
            'id', 'interest_amount', 'total_amount', 'monthly_payment',
            'approved_by', 'approved_at', 'disbursed_at', 'created_at'
        ]


class LoanCreateSerializer(serializers.Serializer):
    loan_type = serializers.ChoiceField(choices=['personal', 'business', 'emergency', 'salary_advance'])
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=100)
    purpose = serializers.CharField()
    term_months = serializers.IntegerField(min_value=1, max_value=60)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=4, required=False)


class LoanApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanApproval
        fields = ['id', 'loan', 'action', 'reviewed_by', 'notes', 'created_at']
        read_only_fields = ['id', 'reviewed_by', 'created_at']


class LoanRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRepayment
        fields = [
            'id', 'loan', 'installment_number', 'amount', 'principal', 'interest',
            'penalty', 'balance_before', 'balance_after', 'due_date', 'paid_date',
            'status', 'payment_method', 'reference_number', 'created_at'
        ]
        read_only_fields = [
            'id', 'principal', 'interest', 'penalty',
            'balance_before', 'balance_after', 'created_at'
        ]


class RepaymentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=1)
    payment_method = serializers.ChoiceField(choices=['telebirr', 'bank_transfer', 'cash'])
    phone_number = serializers.CharField(required=False, allow_blank=True)
    bank_name = serializers.CharField(required=False, allow_blank=True)
    reference_number = serializers.CharField(required=False, allow_blank=True)


class LoanStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approved', 'rejected', 'disbursed'])
    notes = serializers.CharField(required=False, allow_blank=True)