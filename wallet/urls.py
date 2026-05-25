from django.urls import path
from .views import (
    WalletDetailView, DepositView, WithdrawView,
    TransactionHistoryView, InterestRuleListView,
    PenaltyRuleListView, ManualTransactionView
)

urlpatterns = [
    path('', WalletDetailView.as_view(), name='wallet_detail'),
    path('deposit/', DepositView.as_view(), name='deposit'),
    path('withdraw/', WithdrawView.as_view(), name='withdraw'),
    path('transactions/', TransactionHistoryView.as_view(), name='transaction_history'),
    path('interest-rules/', InterestRuleListView.as_view(), name='interest_rules'),
    path('penalty-rules/', PenaltyRuleListView.as_view(), name='penalty_rules'),
    path('manual/', ManualTransactionView.as_view(), name='manual_transaction'),
]