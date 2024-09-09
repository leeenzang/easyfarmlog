from django.urls import path
from .views import DashboardView, PreviousRecordsView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('previous-records/', PreviousRecordsView.as_view(), name='previous-records'),
]