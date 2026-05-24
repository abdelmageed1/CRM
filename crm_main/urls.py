from django.contrib import admin
from django.urls import path, include
from crm_calls_sales import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- General / Authentication URLs ---
    path('', auth_views.login_view, name='login_root'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),

    # --- Apps URLs ---
    path('sales/', include('crm_calls_sales.urls')),
    path('manager/', include('manager.urls')),
    path('accountant/', include('accountant.urls')),
    path('designer/', include('designer.urls')),
]

handler404 = 'crm_calls_sales.views.custom_page_not_found'
# handler500 = 'crm_calls_sales.views.custom_page_not_found'
# handler403 = 'crm_calls_sales.views.custom_page_not_found'
# handler400 = 'crm_calls_sales.views.custom_page_not_found'