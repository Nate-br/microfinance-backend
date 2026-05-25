from rest_framework import serializers
from .models import Wallet, SavingsTransaction, InterestRule, PenaltyRule


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = [
            'id', 'balance', 'available_balance', 'frozen_balance',
            'total_saved', 'total_interest_earned', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SavingsTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsTransaction
        fields = [
            'id', 'transaction_type', 'payment_method', 'amount',
            'balance_before', 'balance_after', 'reference_number',
            'description', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'balance_before', 'balance_after', 'reference_number', 'created_at']


class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=1)
    payment_method = serializers.ChoiceField(choices=['telebirr', 'bank_transfer', 'cash'])
    phone_number = serializers.CharField(required=False, allow_blank=True)
    bank_name = serializers.CharField(required=False, allow_blank=True)
    account_number = serializers.CharField(required=False, allow_blank=True)
    reference_number = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)


class WithdrawSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=1)
    payment_method = serializers.ChoiceField(choices=['telebirr', 'bank_transfer', 'cash'])
    phone_number = serializers.CharField(required=False, allow_blank=True)
    bank_name = serializers.CharField(required=False, allow_blank=True)
    account_number = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)


class InterestRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestRule
        fields = ['id', 'name', 'rate', 'is_active', 'min_balance', 'max_balance', 'created_at']


class PenaltyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PenaltyRule
        fields = ['id', 'name', 'rate', 'grace_period_days', 'is_active', 'description', 'created_at']