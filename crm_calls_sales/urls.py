from django.urls import path
from . import views

urlpatterns = [
    # Dashboard — auto-redirects based on role
    path('dashboard/', views.dashboard, name='dashboard'),

    # Sales Leader dashboard
    path('leader/', views.leader_dashboard, name='leader_dashboard'),
    path('leader/salesperson/<str:owner_name>/', views.leader_salesperson, name='leader_salesperson'),

    # Clients
    path('clients/', views.clients_list, name='clients'),
    path('clients/new/', views.new_client, name='new_client'),
    path('clients/<int:pk>/edit/', views.edit_client, name='edit_client'),
    path('clients/<int:pk>/delete/', views.delete_client, name='delete_client'),
    
    # Edit Requests
    path('edit-requests/my/', views.my_edit_requests, name='my_edit_requests'),
    path('edit-requests/pending/', views.pending_edit_requests, name='pending_edit_requests'),
    path('edit-requests/log/', views.edit_requests_log, name='edit_requests_log'),
    path('edit-requests/<int:request_id>/', views.view_edit_request, name='view_edit_request'),
    path('edit-requests/<int:request_id>/approve/', views.approve_edit_request, name='approve_edit_request'),
    path('edit-requests/<int:request_id>/reject/', views.reject_edit_request, name='reject_edit_request'),
]
