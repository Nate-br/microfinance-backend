from django.urls import path
from .views import (
    LoanApplicationView, MyLoansView, LoanDetailView,
    LoanApprovalListView, LoanApprovalView, LoanDisbursementView,
    RepaymentScheduleView, MakeRepaymentView, LoanHistoryView, AllLoansView
)

urlpatterns = [
    path('apply/', LoanApplicationView.as_view(), name='loan_apply'),
    path('my-loans/', MyLoansView.as_view(), name='my_loans'),
    path('<int:pk>/', LoanDetailView.as_view(), name='loan_detail'),
    path('<int:pk>/repayments/', RepaymentScheduleView.as_view(), name='repayment_schedule'),
    path('<int:pk>/repay/', MakeRepaymentView.as_view(), name='make_repayment'),
    path('pending/', LoanApprovalListView.as_view(), name='loan_pending_list'),
    path('<int:pk>/approve/', LoanApprovalView.as_view(), name='loan_approve'),
    path('<int:pk>/disburse/', LoanDisbursementView.as_view(), name='loan_disburse'),
    path('history/', LoanHistoryView.as_view(), name='loan_history'),
    path('all/', AllLoansView.as_view(), name='all_loans'),
]