from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from django.utils import timezone
from core.custom_permissions import SuperAdminPermission
from backend.models.coremodels import *
from backend.serializers.registercourseserializers import *
from backend.models.allmodels import (
    Course,
    CourseRegisterRecord,
    CourseEnrollment,
)
from core.constants import filtered_display_list, manage_status_list


class LMSCustomerListView(APIView):
    """
    GET API for super admin to list of customers who have resource privilege of LMS and are active
    """
    permission_classes = [SuperAdminPermission]
    
    def get(self, request, format=None):
        try:
            customer_ids_with_lms = CustomerResources.objects.filter(resource__resource_name='LMS').values_list('customer_id', flat=True)
            
            if not customer_ids_with_lms:
                return Response({"error": "No customers found with LMS resource privilege."}, status=status.HTTP_404_NOT_FOUND)
            customers = Customer.objects.filter(id__in=customer_ids_with_lms, is_active=True)
            
            if not customers:
                return Response({"error": "No active customers found with LMS resource privilege."}, status=status.HTTP_404_NOT_FOUND)
            serializer = CustomerSerializer(customers, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            if isinstance(e, (CustomerResources.DoesNotExist, Customer.DoesNotExist)):
                raise NotFound("Record not found or related records not found.")
            elif isinstance(e, ValidationError):
                return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseCustomerRegistrationView(APIView):
    """
    GET API for super admin to list of registration records or single instance based on query parameters passed
    
    POST API for super admin to create new instances of registration records
    
    PUT API for super admin to delete selected instances of registration records

    """ 
    permission_classes = [SuperAdminPermission]
    
    def get(self, request, *args, **kwargs):
        try:
            filtered_display = self.request.query_params.get('filtered_display')
            if filtered_display not in filtered_display_list:
                return Response({"error": "Invalid filtered_display parameter"}, status=status.HTTP_400_BAD_REQUEST)
            
            queryset = CourseRegisterRecord.objects.filter(deleted_at__isnull=True).order_by('-created_at')
            if filtered_display == "active":
                queryset = queryset.filter(active=True)
            elif filtered_display == "inactive":
                queryset = queryset.filter(active=False)
            course_register_records = queryset.all()
            if not course_register_records.exists():
                return Response({"message": "No course register records found.", "data": []}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = DisplayCourseRegisterRecordSerializer(course_register_records, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, *args, **kwargs):
        course_ids = request.data.get("course_id", [])
        customer_ids = request.data.get("customer_id", [])
        
        if not course_ids :
            return Response({"error": "Course IDs are missing"}, status=status.HTTP_400_BAD_REQUEST)
        if not customer_ids:
            return Response({"error": "Customer IDs are missing"}, status=status.HTTP_400_BAD_REQUEST)
        
        created_records = []
        existing_records = []
        
        try:
            for course_id in course_ids:
                course = Course.objects.get(pk=course_id)
                
                if not course:
                    return Response({"message": "No course found.", "data": []}, status=status.HTTP_404_NOT_FOUND)
                for customer_id in customer_ids:
                    customer = Customer.objects.get(pk=customer_id)
                    if not customer:
                        return Response({"message": "No customer found.", "data": []}, status=status.HTTP_404_NOT_FOUND)
                    # Check if record already exists
                    if CourseRegisterRecord.objects.filter(course=course_id, customer=customer_id, deleted_at__isnull=True ).exists():
                        record = CourseRegisterRecord.objects.get(course=course_id, customer=customer_id)
                        if record.active == False:
                            record.active = True
                            record_data = {
                                "id": record.id,
                                "customer": record.customer.id,
                                "course": record.course.id,
                                "created_at": record.created_at,
                                "active": record.active
                            }
                            existing_records.append(record_data)
                        else:
                            record_data = {
                                "id": record.id,
                                "customer": record.customer.id,
                                "course": record.course.id,
                                "created_at": record.created_at,
                                "active": record.active
                            }
                            existing_records.append(record_data)
                            continue 
                    record_data = {
                        'course': course.id,
                        'customer': customer.id,
                        'active': True
                    }
                    
                    serializer = CourseRegisterRecordSerializer(data=record_data)
                    if serializer.is_valid():
                        record = serializer.save()
                        created_records.append(serializer.data)
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            all_records = created_records + existing_records
            return Response({
                "message": "Course register records created successfully.",
                "created_records": created_records,
                "existing_records": existing_records,
                "records":all_records
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            pk = request.data.get('pk')
            registered_record = CourseRegisterRecord.objects.get(pk=pk)
            
            if not registered_record:
                return Response({"message": "No registration record found.", "data": []}, status=status.HTTP_404_NOT_FOUND)
            
            customer_id = registered_record.customer.id
            enroll_records = CourseEnrollment.objects.filter(user__customer__id=customer_id)
            if not enroll_records:
                return Response({"message": "No enroll records found.", "data": []}, status=status.HTTP_404_NOT_FOUND)
            for record in enroll_records:
                record.active = False
                record.deleted_at = timezone.now()
                record.save()
            # Delete the record instance
            registered_record.active = False
            registered_record.deleted_at = timezone.now()
            registered_record.save()
            return Response({"message": f"Record with ID {pk} deleted successfully."}, status=status.HTTP_200_OK)
        
        except Exception as e:
            if isinstance(e, ValidationError):
                return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ManageCourseRegistrationRecordStatusView(APIView):
    """
    POST API for super admin to manage the instance of course registration record according to passed parameter.
    """
    permission_classes = [SuperAdminPermission]
    
    def post(self, request, *args, **kwargs):
        try:
            manage_status = self.request.query_params.get('manage_status')
            if manage_status not in manage_status_list:
                return Response({"error": "Invalid manage_status parameter"}, status=status.HTTP_400_BAD_REQUEST)
            record_ids = request.data.get("records", [])
            if not record_ids:
                return Response({"error": "Record IDs are missing"}, status=status.HTTP_400_BAD_REQUEST)
            
            activated_records = []
            deactivated_records = []
            
            for record_id in record_ids:
                record = CourseRegisterRecord.objects.get(pk=record_id)
                if not record:
                    return Response({"error": f"Record with ID {record_id} not found"}, status=status.HTTP_404_NOT_FOUND)
                if manage_status == "activate":
                    if not record.active and record.deleted_at is None:
                        record.active = True
                        record.updated_at = timezone.now()
                        record.save()
                        activated_records.append(record_id)
                elif manage_status == "inactivate":
                    if record.active and record.deleted_at is None:
                        record.active = False
                        record.updated_at = timezone.now()
                        record.save()
                        deactivated_records.append(record_id)
            
            if manage_status == "activate":
                message = "Course registration records activated successfully."
                records = activated_records
            elif manage_status == "inactivate":
                message = "Course registration records deactivated successfully."
                records = deactivated_records
            
            if records:
                return Response({"message": message, f"{manage_status}_records": records}, status=status.HTTP_200_OK)
            else:
                return Response({"message": f"No records {manage_status}d."}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
