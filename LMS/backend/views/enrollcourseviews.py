from datetime import timezone
from django.forms import ValidationError
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from django.db import transaction
from django.db import DatabaseError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from core.custom_permissions import ClientAdminPermission,IsClientOrAdmin
from backend.models.coremodels import User
from backend.models.allmodels import (
    Course,
    CourseRegisterRecord,
    CourseEnrollment
)
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from  backend.serializers.enrollcourseserializers import (
    CourseEnrollmentSerializer,
    DisplayCourseEnrollmentSerializer,
    EnrolledCoursesSerializer,
    EnrollmentDeleteSerializer,
    ManageCourseEnrollmentSerializer, 
    RegisteredCourseSerializer, 
    UserSerializer
)
from backend.models import *

class DisplayCourseListView(APIView):
    """
    GET REQUEST: - client admin: display courses enrolled
                 - client: display list of courses that client has been enrolled in
    """
    permission_classes = [IsClientOrAdmin]

    def get(self, request, format=None):
        try:
            if request.data.get("customer_id"):
                # Check if the user is a client admin
                customer_id = request.data.get("customer_id")
                if not customer_id:
                    return Response({"error": "Customer ID is required in the request body."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Filter CourseRegisterRecord with customer ID and active status
                course_register_records = CourseRegisterRecord.objects.filter(customer=customer_id, active=True)

                # Check if courses exist
                if not course_register_records:
                    return Response({"message": "No customer-course register record found.", "data": []},
                                    status=status.HTTP_404_NOT_FOUND)

                # Get the list of course IDs
                course_ids = [record.course.id for record in course_register_records]

                # Get instances of Course whose IDs are in the list
                courses = Course.objects.filter(id__in=course_ids)

                # Serialize the courses data
                serializer = RegisteredCourseSerializer(courses, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

            elif request.data.get("user_id"):
                # Check if the user is a client
                user_id = request.data.get("user_id")
                if not user_id:
                    return Response({"error": "User ID is required in the request body."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Retrieve enrolled courses for the user that are active
                enrolled_courses = CourseEnrollment.objects.filter(user=user_id, active=True)

                # Serialize the enrolled courses data
                serializer = EnrolledCoursesSerializer(enrolled_courses, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UserListForEnrollmentView(APIView):
    """
    GET REQUEST 
    view to display data about list of user which have customer id same as that of user in request.            
    """
    permission_classes = [ClientAdminPermission]
    
    def get(self, request, format=None):
        try:
            # Extract customer ID from the request body
            customer_id = request.data.get("customer_id")
            if not customer_id:
                return Response({"error": "Customer ID is missing in the request body."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Filter users based on the provided customer ID
            users = User.objects.filter(customer__id=customer_id)
            if not users:
                return Response({"error": "No users found for the given customer ID."}, status=status.HTTP_404_NOT_FOUND)

            # Serialize the user data
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CourseEnrollmentView(APIView):
    '''
    GET - display list of course enrollments
    POST - enrolling user for courses
    PATCH - delete enrollment
    '''
    permission_classes = [ClientAdminPermission]
    
    def get(self, request, format=None):
        try:
            # Extract user data from the request body
            user_data = request.data.get("user")
            if not user_data:
                return Response({"error": "User data not found in the request body."}, status=status.HTTP_400_BAD_REQUEST)

            # Extract the role from the user data
            role = user_data.get("role")

            # Get all instances of CourseEnrollment
            enrollments = CourseEnrollment.objects.all()
            print("Role extracted from user data:", role)
            # Filter enrollments based on the role if provided
            # if role is not None:
            #     enrollments = enrollments.filter(user__role=role)
            if not enrollments.exists():
                return Response({"message": "No course enrollments found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = DisplayCourseEnrollmentSerializer(enrollments, many=True)
            
            return Response(serializer.data)
        except (CourseEnrollment.DoesNotExist, DatabaseError, ValidationError) as error:
            error_message = "An error occurred: " + str(error)
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def post(self, request, *args, **kwargs):
        try:

            # Validate request data using the serializer
            serializer = CourseEnrollmentSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Extract validated course_ids and user_ids from serializer data
            course_ids = serializer.validated_data.get("course_ids")
            user_ids = serializer.validated_data.get("user_ids")

            # Lists to hold created enrollments, existing records, and all records
            enrollments = []
            existing_records = []

            # Retrieve all existing records from the database
            all_existing_records = CourseEnrollment.objects.all()

            # Iterate through course_ids and user_ids to create enrollments
            for course_id in course_ids:
                for user_id in user_ids:
                    # Check if enrollment already exists
                    record = CourseEnrollment.objects.filter(course_id=course_id, user_id=user_id).first()
                    if record:
                        # Update active status if False
                        if not record.active:
                            record.active = True
                            record_data = {
                                "id": record.id,
                                "course": record.course.id,
                                "active": record.active
                            }
                            existing_records.append(record_data)
                        else:
                            record_data = {
                                "id": record.id,
                                "course": record.course.id,
                                "active": record.active
                            }
                            existing_records.append(record_data)
                        continue  # Move to the next iteration

                    # Create a new enrollment
                    enrollment = CourseEnrollment.objects.create(course_id=course_id, user_id=user_id, active=True)
                    enrollments.append(enrollment)

            # Combine new enrollments and existing records into a single list
            all_records = list(all_existing_records.values()) + enrollments + existing_records

            # Response body including all three lists
            response_data = {
                "message": "Course enrollments have been created successfully.",
                "enrollments": enrollments,
                "existing_records": existing_records,
                "all_records": all_records
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, format=None):
        # Initialize serializer with request data
        serializer = EnrollmentDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Raise validation error if invalid

        try:
            enrollment_id = serializer.validated_data['enrollment_id']
            
            # Check if the enrollment exists
            enrollment = CourseEnrollment.objects.get(pk=enrollment_id)
            
            # Check if the enrollment is already soft-deleted
            if enrollment.deleted_at:
                return Response({"error": "Course enrollment is already deleted."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Soft delete the enrollment
            enrollment.deleted_at = timezone.now()
            enrollment.active = False
            enrollment.save()

            return Response({"message": "Course enrollment deleted successfully."}, status=status.HTTP_200_OK)
        
        except Exception as e:
            if isinstance(e, CourseEnrollment.DoesNotExist):
                return Response({"error": f"Course enrollment with ID {enrollment_id} not found."}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class ManageCourseEnrollmentView(APIView):
    """
    This API is used to manage course enrollment for specified user(s).
    Method: POST
    """
    permission_classes = [ClientAdminPermission]
    def post(self, request, *args, **kwargs):
        try:
            # Extract the 'action' parameter from the query parameters
            action = request.query_params.get('action')

            # Deserialize and validate the input data
            serializer = ManageCourseEnrollmentSerializer(data=request.data)
            if serializer.is_valid():
                enrollment_ids = serializer.validated_data.get('enrollment_ids')

                # Check if any enrollment IDs were provided
                if not enrollment_ids:
                    return Response({'error': 'No enrollment IDs provided'}, status=status.HTTP_400_BAD_REQUEST)

                # Check if any provided enrollment IDs are not found in the database
                enrollments = CourseEnrollment.objects.filter(id__in=enrollment_ids)
                if len(enrollments) != len(enrollment_ids):
                    return Response({'error': 'One or more enrollment IDs do not exist'}, status=status.HTTP_404_NOT_FOUND)

                # Perform the action based on the specified action parameter
                if action == 'unassign':
                    updated_enrollments = self.unassign_courses(enrollments)
                elif action == 'assign':
                    updated_enrollments = self.assign_courses(enrollments)
                else:
                    return Response({'error': 'Invalid action specified'}, status=status.HTTP_400_BAD_REQUEST)

                return Response({'message': f'Courses {action}ed successfully.', 'updated_enrollments': updated_enrollments}, status=status.HTTP_200_OK)

            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def unassign_courses(self, enrollments):
        """
        Unassign courses for the specified enrollments.
        """
        updated_enrollments = []
        for enrollment in enrollments:
            if enrollment.active:
                enrollment.active = False
                enrollment.save()
                updated_enrollments.append(enrollment.id)
            else:
                updated_enrollments.append({'id': enrollment.id, 'message': 'Enrollment is already inactive'})
        return updated_enrollments

    def assign_courses(self, enrollments):
        """
        Assigns courses for the specified enrollments.
        """
        updated_count = 0
        enrollments_to_update = enrollments.filter(active=False)
        if enrollments_to_update.exists():
            with transaction.atomic():
                updated_count = enrollments_to_update.update(active=True)
        return updated_count