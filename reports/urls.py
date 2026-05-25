from django.urls import path
from .views import DashboardStatsView, CustomerStatsView, TransactionReportView, LoanReportView, ExportReportView

urlpatterns = [
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('customer-stats/', CustomerStatsView.as_view(), name='customer_stats'),
    path('transactions/', TransactionReportView.as_view(), name='transaction_report'),
    path('loans/', LoanReportView.as_view(), name='loan_report'),
    path('export/', ExportReportView.as_view(), name='export_report'),
]