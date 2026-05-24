from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('sales', 'Sales'),
        ('sales_leader', 'Sales Leader'),
        ('manager'    , 'Manager'),
        ('admin'       , 'Admin'),
        ('accountant' , 'Accountant'),
        ('designer'   , 'Designer'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    email = models.EmailField( blank=True, null=True)


    def __str__(self):
        return f"{self.username} — {self.get_role_display()}"

    @property
    def is_sales(self):
        return self.role == 'sales'

    @property
    def is_sales_leader(self):
        return self.role == 'sales_leader'

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_system_admin(self):
        return self.role == 'admin'

    @property
    def is_accountant(self):
        return self.role == 'accountant'

    @property
    def is_designer(self):
        return self.role == 'designer'
