from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now


class Customer(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=255, default='active', null=True)
    is_active = models.BooleanField(default=True, null=True)
    is_deleted = models.BooleanField(default=False, null=True)
    email = models.EmailField(unique=True, null=True)
    customer_resources = models.ManyToManyField('CustomerResources', related_name='customer_resources')

    class Meta:
        db_table = 'customer'
        verbose_name_plural = 'Customers'


class Role(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    class Meta:
        db_table = 'role'

class User(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    role = models.IntegerField(null=True)
    email = models.EmailField(unique=True, null=True)
    password = models.CharField(max_length=255, null=True)
    access_token = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=255, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived')
    ], default='active', null=True)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='users')
    created_by = models.ForeignKey('Role', on_delete=models.CASCADE, related_name='created_users')

    class Meta:
        db_table = 'users'


class UserRolePrivileges(models.Model):
    id = models.AutoField(primary_key=True)
    role = models.ForeignKey('Role', on_delete=models.CASCADE, related_name='role_privileges')
    resource = models.ForeignKey('Resources', on_delete=models.CASCADE, related_name='role_privileges')
    has_read = models.BooleanField(default=True, null=False)
    has_write = models.BooleanField(default=False, null=False)

    class Meta:
        db_table = 'user_role_privileges'
        verbose_name_plural = 'User Role Privileges'


class Resources(models.Model):
    id = models.AutoField(primary_key=True)
    resource_name = models.CharField(max_length=255, null=False)
    status = models.IntegerField(default=0, null=False)
    parent_id = models.IntegerField(null=True)

    class Meta:
        db_table = 'resources'
        verbose_name_plural = 'Resources'


class CustomerResources(models.Model):
    id = models.AutoField(primary_key=True)
    resource = models.ForeignKey('Resources', on_delete=models.CASCADE, related_name='customer_resource')
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='customer_resource')
    access_type = models.IntegerField(null=True)

    class Meta:
        db_table = 'customer_resources'
        verbose_name_plural = 'Customer Resources'

