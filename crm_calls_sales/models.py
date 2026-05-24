from django.db import models
from django.conf import settings
import json


class CallsResponse(models.Model):
    """Maps to calls_response table in sheets_calls DB"""
    lead_owner = models.TextField(blank=True, null=True)
    phone_number = models.TextField(blank=True, null=True)
    client_code = models.TextField(blank=True, null=True)
    client_name = models.TextField(blank=True, null=True)
    project_name = models.TextField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    email_address = models.EmailField(blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    manager_comments = models.TextField(blank=True, null=True)
    standard_lead_owner = models.TextField(blank=True, null=True)
    broker_name = models.TextField(blank=True, null=True)
    id = models.IntegerField(primary_key=True)

    class Meta:
        db_table = 'calls_response'
        managed = False

    def __str__(self):
        return f"{self.client_name} - {self.project_name}"


class ClientEditRequest(models.Model):
    """Stores edit requests from sales users that need leader approval"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # من قام بالطلب
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='edit_requests')
    
    # العميل المراد تعديله
    client_id = models.IntegerField()
    client_name = models.CharField(max_length=255)
    
    # البيانات القديمة والجديدة (JSON format)
    old_data = models.TextField(help_text="JSON of old client data")
    new_data = models.TextField(help_text="JSON of new client data")
    
    # سبب التعديل
    reason = models.TextField(blank=True, null=True, help_text="Reason for the edit request")
    
    # حالة الطلب
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # من راجع الطلب
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    review_notes = models.TextField(blank=True, null=True)
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'crm_client_edit_request'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Edit request by {self.requested_by.username} for {self.client_name} - {self.status}"
    
    def get_old_data_dict(self):
        """Returns old data as dictionary"""
        return json.loads(self.old_data) if self.old_data else {}
    
    def get_new_data_dict(self):
        """Returns new data as dictionary"""
        return json.loads(self.new_data) if self.new_data else {}
    
    def get_changes_summary(self):
        """Returns a summary of what changed"""
        old = self.get_old_data_dict()
        new = self.get_new_data_dict()
        changes = {}
        
        for key in new:
            if key in old and old[key] != new[key]:
                changes[key] = {
                    'old': old[key],
                    'new': new[key]
                }
        
        return changes
