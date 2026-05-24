from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib import messages
from django.db.models import Q, Count
from django.db import connection
from django.utils import timezone
from datetime import datetime
from .models import CallsResponse, ClientEditRequest
import json


# ---------------------------------------------------------------------------
# helpers

def custom_page_not_found(request, exception):
    return render(request, '404.html', status=404)    

# ---------------------------------------------------------------------------




def db_name(user):
    """Convert username / full-name dot-notation to DB space-notation."""
    name = user.get_full_name() or user.username
    return str(name).replace('.', ' ').strip()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'crm/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ---------------------------------------------------------------------------
# Dashboard — redirects to role-specific view
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    user = request.user
    # Redirect superuser to admin first, regardless of role
    if user.is_superuser:
        return redirect('/admin/')
    elif user.is_sales_leader:
        return redirect('leader_dashboard')
    elif user.is_manager:
        return redirect('manager:dashboard')
    elif user.is_accountant:
        return redirect('accountant:dashboard')
    elif user.is_designer:
        return redirect('designer:dashboard')
    elif user.is_system_admin:
        return redirect('/admin/')
    
    return sales_dashboard(request)


# ---------------------------------------------------------------------------
# Sales dashboard (personal stats)
# ---------------------------------------------------------------------------

def sales_dashboard(request):
    profile = request.user
    user_db_name = db_name(request.user)
    clients = CallsResponse.objects.filter(
        standard_lead_owner__iexact=user_db_name
    )

    total        = clients.count()
    interested   = clients.filter(status='Interested').count()
    not_interested = clients.filter(status='Not interested').count()
    scheduled    = clients.filter(status='Scheduled a meeting').count()
    recent       = clients.order_by('-id')[:5]

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT project_name, COUNT(*) as cnt
            FROM calls_response
            WHERE LOWER(TRIM(standard_lead_owner)) = LOWER(%s)
              AND project_name IS NOT NULL
              AND project_name != ''
            GROUP BY project_name
            ORDER BY cnt DESC
            LIMIT 5
        """, [user_db_name])
        project_stats = cursor.fetchall()

    context = {
        'total': total,
        'interested': interested,
        'not_interested': not_interested,
        'scheduled': scheduled,
        'recent_clients': recent,
        'project_stats': project_stats,
        'profile': profile,
    }
    return render(request, 'crm/dashboard.html', context)


# ---------------------------------------------------------------------------
# Clients list — Sales sees own, Leader sees all (optionally filtered)
# ---------------------------------------------------------------------------

@login_required
def clients_list(request):
    profile = request.user
    query         = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    owner_filter  = request.GET.get('owner', '')
    location_filter = request.GET.get('location', '')
    date_from_str  = request.GET.get('date_from', '')
    date_to_str    = request.GET.get('date_to', '')

    if profile.is_sales_leader:
        clients = CallsResponse.objects.all().order_by('-id')
        if owner_filter:
            clients = clients.filter(standard_lead_owner__iexact=owner_filter)
        # Build list of distinct owners for filter dropdown
        owners = (
            CallsResponse.objects
            .exclude(standard_lead_owner__isnull=True)
            .exclude(standard_lead_owner='')
            .values_list('standard_lead_owner', flat=True)
            .distinct()
            .order_by('standard_lead_owner')
        )
    else:
        user_db_name = db_name(request.user)
        clients = CallsResponse.objects.filter(
            standard_lead_owner__iexact=user_db_name
        ).order_by('-id')
        owners = None

    # Build list of distinct locations for filter dropdown (available to all users)
    locations = (
        CallsResponse.objects
        .exclude(location__isnull=True)
        .exclude(location='')
        .values_list('location', flat=True)
        .distinct()
        .order_by('location')
    )

    if query:
        clients = clients.filter(
            Q(client_name__icontains=query) |
            Q(project_name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(email_address__icontains=query)
        )
    if status_filter:
        clients = clients.filter(status=status_filter)
    if location_filter:
        clients = clients.filter(location=location_filter)
    # Date range filtering (accepts YYYY-MM-DD)
    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        except Exception:
            date_from = None
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
        except Exception:
            date_to = None
    if date_from:
        clients = clients.filter(date__gte=date_from)
    if date_to:
        clients = clients.filter(date__lte=date_to)

    context = {
        'clients': clients,
        'query': query,
        'status_filter': status_filter,
        'owner_filter': owner_filter,
        'location_filter': location_filter,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'owners': owners,
        'locations': locations,
        'profile': profile,
    }
    return render(request, 'crm/clients.html', context)


# ---------------------------------------------------------------------------
# New client — both roles can add
# ---------------------------------------------------------------------------

@login_required
def new_client(request):
    from .forms import ClientForm
    profile = request.user
    user_db_name = db_name(request.user)

    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM calls_response")
                next_id = cursor.fetchone()[0]
            # Combine project name choice and user-provided unit
            proj_choice = form.cleaned_data.get('project_name', '') or ''
            proj_unit = form.cleaned_data.get('project_unit', '') or ''
            # If user selected 'other', store the unit field as the full project name
            if proj_choice == 'other' or proj_choice == '':
                combined_project = proj_unit.strip()
            else:
                combined_project = f"{proj_choice} {proj_unit}".strip()

            client = CallsResponse(
                id=next_id,
                lead_owner=form.cleaned_data['lead_owner'],
                phone_number=form.cleaned_data['phone_number'],
                client_code=form.cleaned_data['client_code'],
                client_name=form.cleaned_data['client_name'],
                project_name=combined_project,
                date=form.cleaned_data['date'],
                notes=form.cleaned_data.get('notes', ''),
                status=form.cleaned_data['status'],
                type=form.cleaned_data.get('type', ''),
                email_address=form.cleaned_data['email_address'],
                location=form.cleaned_data['location'],
                manager_comments=form.cleaned_data.get('manager_comments', ''),
                standard_lead_owner=user_db_name,
                broker_name=form.cleaned_data.get('broker_name', ''),
            )
            client.save()
            messages.success(request, f'Client "{client.client_name}" added successfully!')
            return redirect('clients')
    else:
        form = ClientForm(initial={'lead_owner': user_db_name})

    return render(request, 'crm/new_client.html', {
        'form': form,
        'user_name': user_db_name,
        'profile': profile,
    })


# ---------------------------------------------------------------------------
# Edit client — Leader edits directly, Sales creates edit request
# ---------------------------------------------------------------------------

@login_required
def edit_client(request, pk):
    from .forms import ClientForm
    profile = request.user
    client = get_object_or_404(CallsResponse, pk=pk)

    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            # إذا كان Leader، يعدل مباشرة
            if profile.is_sales_leader:
                client.lead_owner        = form.cleaned_data['lead_owner']
                client.phone_number      = form.cleaned_data['phone_number']
                client.client_code       = form.cleaned_data['client_code']
                client.client_name       = form.cleaned_data['client_name']
                # merge project name + unit; if 'other' selected, use unit as full name
                proj_choice = form.cleaned_data.get('project_name', '') or ''
                proj_unit = form.cleaned_data.get('project_unit', '') or ''
                if proj_choice == 'other' or proj_choice == '':
                    client.project_name = proj_unit.strip()
                else:
                    client.project_name = f"{proj_choice} {proj_unit}".strip()
                client.date              = form.cleaned_data['date']
                client.notes             = form.cleaned_data.get('notes', '')
                client.status            = form.cleaned_data['status']
                client.type              = form.cleaned_data.get('type', '')
                client.email_address     = form.cleaned_data['email_address']
                client.location          = form.cleaned_data['location']
                client.manager_comments  = form.cleaned_data.get('manager_comments', '')
                client.broker_name       = form.cleaned_data.get('broker_name', '')
                client.save()
                messages.success(request, f'تم تحديث بيانات العميل "{client.client_name}" بنجاح!')
                return redirect('clients')
            
            # إذا كان Sales عادي، ينشئ طلب تعديل
            else:
                # البيانات القديمة
                old_data = {
                    'lead_owner': client.lead_owner,
                    'phone_number': client.phone_number,
                    'client_code': client.client_code,
                    'client_name': client.client_name,
                    'project_name': client.project_name,
                    'date': str(client.date) if client.date else None,
                    'notes': client.notes,
                    'status': client.status,
                    'type': client.type,
                    'email_address': client.email_address,
                    'location': client.location,
                    'manager_comments': client.manager_comments,
                    'broker_name': client.broker_name,
                }
                
                # البيانات الجديدة
                new_data = {
                    'lead_owner': form.cleaned_data['lead_owner'],
                    'phone_number': form.cleaned_data['phone_number'],
                    'client_code': form.cleaned_data['client_code'],
                    'client_name': form.cleaned_data['client_name'],
                    # if project choice is 'other' send the detailed unit as project_name
                    'project_name': (
                        form.cleaned_data.get('project_unit','').strip()
                        if form.cleaned_data.get('project_name','') in ('other','')
                        else f"{form.cleaned_data.get('project_name','')} {form.cleaned_data.get('project_unit','')}".strip()
                    ),
                    'date': str(form.cleaned_data['date']) if form.cleaned_data['date'] else None,
                    'notes': form.cleaned_data.get('notes', ''),
                    'status': form.cleaned_data['status'],
                    'type': form.cleaned_data.get('type', ''),
                    'email_address': form.cleaned_data['email_address'],
                    'location': form.cleaned_data['location'],
                    'manager_comments': form.cleaned_data.get('manager_comments', ''),
                    'broker_name': form.cleaned_data.get('broker_name', ''),
                }
                
                # إنشاء طلب التعديل
                edit_request = ClientEditRequest.objects.create(
                    requested_by=request.user,
                    client_id=client.id,
                    client_name=client.client_name,
                    old_data=json.dumps(old_data, ensure_ascii=False),
                    new_data=json.dumps(new_data, ensure_ascii=False),
                    reason=request.POST.get('reason', ''),
                    status='pending'
                )
                
                messages.success(
                    request, 
                    f'تم إرسال طلب تعديل بيانات العميل "{client.client_name}" إلى المدير للموافقة عليه.'
                )
                return redirect('my_edit_requests')
    else:
        # try to split stored project_name into choice + unit
        stored = client.project_name or ''
        proj_choice = ''
        proj_unit = ''
        if stored:
            parts = stored.split(' ', 1)
            first = parts[0]
            known_codes = ('GA', 'GC', 'GJ', 'other')
            if first in known_codes:
                proj_choice = first
                proj_unit = parts[1] if len(parts) > 1 else ''
            else:
                proj_choice = 'other'
                proj_unit = stored

        form = ClientForm(initial={
            'lead_owner':       client.lead_owner,
            'phone_number':     client.phone_number,
            'client_code':      client.client_code,
            'client_name':      client.client_name,
            'project_name':     proj_choice,
            'project_unit':     proj_unit,
            'date':             client.date,
            'notes':            client.notes,
            'status':           client.status,
            'type':             client.type,
            'email_address':    client.email_address,
            'location':         client.location,
            'manager_comments': client.manager_comments,
            'broker_name':      client.broker_name,
        })

    return render(request, 'crm/new_client.html', {
        'form': form,
        'edit': True,
        'client': client,
        'user_name': db_name(request.user),
        'profile': profile,
        'is_sales': profile.is_sales,
    })


# ---------------------------------------------------------------------------
# Delete client — ONLY Sales Leader
# ---------------------------------------------------------------------------

@login_required
def delete_client(request, pk):
    profile = request.user

    if not profile.is_sales_leader:
        messages.error(request, 'ليس لديك صلاحية حذف العملاء.')
        return redirect('clients')

    client = get_object_or_404(CallsResponse, pk=pk)
    if request.method == 'POST':
        name = client.client_name
        client.delete()
        messages.success(request, f'Client "{name}" deleted.')
    return redirect('clients')


# ---------------------------------------------------------------------------
# Leader dashboard — shows all salespeople + per-person stats
# ---------------------------------------------------------------------------

@login_required
def leader_dashboard(request):
    profile = request.user
    if not profile.is_sales_leader:
        return redirect('dashboard')

    # Per-salesperson stats
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                standard_lead_owner,
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Interested' THEN 1 ELSE 0 END)          AS interested,
                SUM(CASE WHEN status = 'Not interested' THEN 1 ELSE 0 END)      AS not_interested,
                SUM(CASE WHEN status = 'Scheduled a meeting' THEN 1 ELSE 0 END) AS scheduled
            FROM calls_response
            WHERE standard_lead_owner IS NOT NULL AND standard_lead_owner != ''
            GROUP BY standard_lead_owner
            ORDER BY total DESC
        """)
        rows = cursor.fetchall()

    sales_stats = []
    for row in rows:
        owner, total, interested, not_interested, scheduled = row
        sales_stats.append({
            'owner': owner,
            'total': total or 0,
            'interested': interested or 0,
            'not_interested': not_interested or 0,
            'scheduled': scheduled or 0,
        })

    # Team totals
    team_total          = sum(s['total'] for s in sales_stats)
    team_interested     = sum(s['interested'] for s in sales_stats)
    team_not_interested = sum(s['not_interested'] for s in sales_stats)
    team_scheduled      = sum(s['scheduled'] for s in sales_stats)
    
    # عدد الطلبات المعلقة
    pending_requests_count = ClientEditRequest.objects.filter(status='pending').count()

    context = {
        'sales_stats': sales_stats,
        'team_total': team_total,
        'team_interested': team_interested,
        'team_not_interested': team_not_interested,
        'team_scheduled': team_scheduled,
        'pending_requests_count': pending_requests_count,
        'profile': profile,
    }
    return render(request, 'crm/leader_dashboard.html', context)


# ---------------------------------------------------------------------------
# Leader: view one salesperson's clients
# ---------------------------------------------------------------------------

@login_required
def leader_salesperson(request, owner_name):
    profile = request.user
    if not profile.is_sales_leader:
        return redirect('dashboard')

    query         = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    clients = CallsResponse.objects.filter(
        standard_lead_owner__iexact=owner_name
    ).order_by('-id')

    if query:
        clients = clients.filter(
            Q(client_name__icontains=query) |
            Q(project_name__icontains=query) |
            Q(phone_number__icontains=query)
        )
    if status_filter:
        clients = clients.filter(status=status_filter)

    total          = clients.count()
    interested     = clients.filter(status='Interested').count()
    not_interested = clients.filter(status='Not interested').count()
    scheduled      = clients.filter(status='Scheduled a meeting').count()

    context = {
        'owner_name': owner_name,
        'clients': clients,
        'query': query,
        'status_filter': status_filter,
        'total': total,
        'interested': interested,
        'not_interested': not_interested,
        'scheduled': scheduled,
        'profile': profile,
    }
    return render(request, 'crm/leader_salesperson.html', context)


# ---------------------------------------------------------------------------
# Edit Requests Management
# ---------------------------------------------------------------------------

@login_required
def my_edit_requests(request):
    """عرض طلبات التعديل الخاصة بالـ Sales"""
    profile = request.user
    
    # السيلز يرى طلباته فقط
    requests = ClientEditRequest.objects.filter(
        requested_by=request.user
    ).order_by('-created_at')
    
    context = {
        'edit_requests': requests,
        'profile': profile,
    }
    return render(request, 'crm/my_edit_requests.html', context)


@login_required
def pending_edit_requests(request):
    """عرض طلبات التعديل المعلقة للـ Leader"""
    profile = request.user
    
    if not profile.is_sales_leader:
        messages.error(request, 'ليس لديك صلاحية الوصول لهذه الصفحة.')
        return redirect('dashboard')
    
    # الطلبات المعلقة فقط
    pending_requests = ClientEditRequest.objects.filter(
        status='pending'
    ).select_related('requested_by').order_by('-created_at')
    
    # إحصائيات
    total_pending = pending_requests.count()
    
    context = {
        'pending_requests': pending_requests,
        'total_pending': total_pending,
        'profile': profile,
    }
    return render(request, 'crm/pending_edit_requests.html', context)


@login_required
def view_edit_request(request, request_id):
    """عرض تفاصيل طلب التعديل"""
    profile = request.user
    edit_request = get_object_or_404(ClientEditRequest, id=request_id)
    
    # التحقق من الصلاحيات
    if not profile.is_sales_leader and edit_request.requested_by != request.user:
        messages.error(request, 'ليس لديك صلاحية عرض هذا الطلب.')
        return redirect('dashboard')
    
    # الحصول على التغييرات
    changes = edit_request.get_changes_summary()
    
    # ترجمة أسماء الحقول للعربية
    field_names = {
        'lead_owner': 'مالك العميل',
        'phone_number': 'رقم الهاتف',
        'client_code': 'كود العميل',
        'client_name': 'اسم العميل',
        'project_name': 'اسم المشروع',
        'date': 'التاريخ',
        'notes': 'الملاحظات',
        'status': 'الحالة',
        'type': 'النوع',
        'email_address': 'البريد الإلكتروني',
        'location': 'الموقع',
        'manager_comments': 'تعليقات المدير',
        'broker_name': 'اسم الوسيط',
    }
    
    # تنسيق التغييرات
    formatted_changes = []
    for field, change in changes.items():
        formatted_changes.append({
            'field': field_names.get(field, field),
            'old_value': change['old'] or '-',
            'new_value': change['new'] or '-',
        })
    
    context = {
        'edit_request': edit_request,
        'changes': formatted_changes,
        'profile': profile,
    }
    return render(request, 'crm/view_edit_request.html', context)


@login_required
def approve_edit_request(request, request_id):
    """الموافقة على طلب التعديل وتطبيق التغييرات"""
    profile = request.user
    
    if not profile.is_sales_leader:
        messages.error(request, 'ليس لديك صلاحية الموافقة على الطلبات.')
        return redirect('dashboard')
    
    edit_request = get_object_or_404(ClientEditRequest, id=request_id)
    
    if edit_request.status != 'pending':
        messages.warning(request, 'هذا الطلب تمت معالجته بالفعل.')
        return redirect('pending_edit_requests')
    
    if request.method == 'POST':
        try:
            # الحصول على العميل
            client = CallsResponse.objects.get(id=edit_request.client_id)
            
            # تطبيق التغييرات
            new_data = edit_request.get_new_data_dict()
            client.lead_owner = new_data.get('lead_owner', client.lead_owner)
            client.phone_number = new_data.get('phone_number', client.phone_number)
            client.client_code = new_data.get('client_code', client.client_code)
            client.client_name = new_data.get('client_name', client.client_name)
            client.project_name = new_data.get('project_name', client.project_name)
            client.date = new_data.get('date', client.date)
            client.notes = new_data.get('notes', client.notes)
            client.status = new_data.get('status', client.status)
            client.type = new_data.get('type', client.type)
            client.email_address = new_data.get('email_address', client.email_address)
            client.location = new_data.get('location', client.location)
            client.manager_comments = new_data.get('manager_comments', client.manager_comments)
            client.broker_name = new_data.get('broker_name', client.broker_name)
            client.save()
            
            # تحديث حالة الطلب
            edit_request.status = 'approved'
            edit_request.reviewed_by = request.user
            edit_request.reviewed_at = timezone.now()
            edit_request.review_notes = request.POST.get('review_notes', '')
            edit_request.save()
            
            messages.success(
                request, 
                f'تمت الموافقة على طلب التعديل وتم تحديث بيانات العميل "{client.client_name}" بنجاح!'
            )
        except CallsResponse.DoesNotExist:
            messages.error(request, 'العميل غير موجود.')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تطبيق التعديلات: {str(e)}')
        
        return redirect('pending_edit_requests')
    
    return redirect('view_edit_request', request_id=request_id)


@login_required
def reject_edit_request(request, request_id):
    """رفض طلب التعديل"""
    profile = request.user
    
    if not profile.is_sales_leader:
        messages.error(request, 'ليس لديك صلاحية رفض الطلبات.')
        return redirect('dashboard')
    
    edit_request = get_object_or_404(ClientEditRequest, id=request_id)
    
    if edit_request.status != 'pending':
        messages.warning(request, 'هذا الطلب تمت معالجته بالفعل.')
        return redirect('pending_edit_requests')
    
    if request.method == 'POST':
        edit_request.status = 'rejected'
        edit_request.reviewed_by = request.user
        edit_request.reviewed_at = timezone.now()
        edit_request.review_notes = request.POST.get('review_notes', '')
        edit_request.save()
        
        messages.success(request, f'تم رفض طلب التعديل.')
        return redirect('pending_edit_requests')
    
    return redirect('view_edit_request', request_id=request_id)


# ---------------------------------------------------------------------------
# Leader: Full Edit Requests Log with search & filter
# ---------------------------------------------------------------------------

@login_required
def edit_requests_log(request):
    """سجل كل طلبات التعديل مع فلتر وبحث — للـ Leader فقط"""
    profile = request.user

    if not profile.is_sales_leader:
        messages.error(request, 'ليس لديك صلاحية الوصول لهذه الصفحة.')
        return redirect('dashboard')

    # Query params
    query         = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sales_filter  = request.GET.get('sales', '')

    # Base queryset – all requests
    edit_requests = ClientEditRequest.objects.select_related(
        'requested_by', 'reviewed_by'
    ).order_by('-created_at')

    # Filter by status
    if status_filter:
        edit_requests = edit_requests.filter(status=status_filter)

    # Filter by sales person
    if sales_filter:
        edit_requests = edit_requests.filter(requested_by__id=sales_filter)

    # Search by client name
    if query:
        edit_requests = edit_requests.filter(
            Q(client_name__icontains=query) |
            Q(requested_by__username__icontains=query) |
            Q(requested_by__first_name__icontains=query) |
            Q(requested_by__last_name__icontains=query)
        )

    # Stats
    all_requests = ClientEditRequest.objects.all()
    total_count    = all_requests.count()
    pending_count  = all_requests.filter(status='pending').count()
    approved_count = all_requests.filter(status='approved').count()
    rejected_count = all_requests.filter(status='rejected').count()

    # List of sales users for filter dropdown
    sales_users = User.objects.filter(
        edit_requests__isnull=False
    ).distinct().order_by('username')

    context = {
        'edit_requests': edit_requests,
        'query': query,
        'status_filter': status_filter,
        'sales_filter': sales_filter,
        'sales_users': sales_users,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'profile': profile,
    }
    return render(request, 'crm/edit_requests_log.html', context)
