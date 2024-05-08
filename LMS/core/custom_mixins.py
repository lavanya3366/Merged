from rest_framework import permissions
from backend.models.coremodels import UserRolePrivileges
import json
from core.constants import (
    super_admin_resources, 
    client_admin_resources, 
    client_resources,
    course_enrollment_id,
    course_registration_id,
    course_management_id,
    dashboard_id
)


'''this is how base permission works :

from rest_framework.permissions import BasePermission

class IsAuthenticated(BasePermission):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

'''

'''
allowed_resources:
1- LMS
2- Course Customer Registration
3- Course Enrollment
4- Courses
5- Course Management
6- Dashboard
'''

class SuperAdminMixin:

    def has_super_admin_privileges(self, request):        
        # user_privileges = UserRolePrivileges.objects.filter(role=request.user.role)
        user = request.data.get('user')
        print("super")
        user_privileges = UserRolePrivileges.objects.filter(role= user['role']) # role= user.role
        privileged_resources = {privilege.resource.id for privilege in user_privileges}
        print(privileged_resources)        
        if super_admin_resources == privileged_resources:
            return True
        # Check for specific super admin privileges
        if course_enrollment_id not in privileged_resources and (course_registration_id in privileged_resources or course_management_id in privileged_resources):
            return True
        return False
    
class ClientAdminMixin:
    
    def has_client_admin_privileges(self, request):
        # user_privileges = UserRolePrivileges.objects.filter(role=request.user.role)
        user = request.data.get('user')
        print("client admin")
        user_privileges = UserRolePrivileges.objects.filter(role= user['role']) # role= user.role
        privileged_resources = {privilege.resource.id for privilege in user_privileges}
        if client_admin_resources == privileged_resources:
            return True
        # Check for specific client admin privileges
        if course_enrollment_id in privileged_resources and not any(resource_id in privileged_resources for resource_id in [course_registration_id, course_management_id]):
            return True
        return False
    
class ClientMixin:
    
    def has_client_privileges(self, request):
        user = request.data.get('user')
        user_privileges = UserRolePrivileges.objects.filter(role= user['role']) # role= user.role
        # user = request.user
        # user_privileges = UserRolePrivileges.objects.filter(role= user.role)
        privileged_resources = {privilege.resource.id for privilege in user_privileges}
        if client_resources == privileged_resources:
            return True
        # Check for specific client privileges
        if dashboard_id in privileged_resources and not any(resource_id in privileged_resources for resource_id in [course_registration_id, course_management_id, course_enrollment_id]):
            return True
        return False
