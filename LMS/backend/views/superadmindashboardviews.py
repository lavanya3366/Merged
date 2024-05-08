# from core.custom_permissions import SuperAdminPermission
from core.custom_permissions import SuperAdminPermission
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from backend.serializers.superadmindashboardserializers import (
    ActiveCourseCountSerializer, 
    ActiveRegistrationCountSerializer, 
    InActiveCourseCountSerializer
)
from backend.models.allmodels import (
    Course,
    CourseCompletionStatusPerUser,
    CourseRegisterRecord,
)
from rest_framework.exceptions import NotFound, ValidationError

# =================================================================
# super admin dashboard
# =================================================================
class ActiveRegisteredCustomerCountView(APIView):
    """
    GET API for super admin to get count active and inactive registrations.
    """
    permission_classes = [SuperAdminPermission]
    def get(self, request):
        try:
            active_registration_count = CourseRegisterRecord.objects.filter(active=True, deleted_at__isnull=True).values('customer').distinct().count()
            if active_registration_count is None:
                return Response({"message": "no active registration were found"}, status=status.HTTP_404_NOT_FOUND)
            serializer = ActiveRegistrationCountSerializer({'active_registered_customer_count': active_registration_count})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            if isinstance(e, ValidationError):
                return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# graph to count registrations per course 
class CountOfActiveRegistrationPerCoure(APIView):
    """
    GET API for super admin to get count active registrations of customers per each courses separately.
    """
    """
        get list of active courses from course table
        and for each course count instances from course registration records which are active =true, deleted_at =null
        and pass this data in response for each course send it's calculated count
    """
    permission_classes = [SuperAdminPermission]
    
    def get(self, request):
        try:
            active_courses = Course.objects.filter(active=True, deleted_at__isnull=True)
            if not active_courses:
                return Response({"message": "no active course found"},status=status.HTTP_404_NOT_FOUND)

            course_active_registration_counts = []
            
            for course in active_courses:
                active_registration_count = CourseRegisterRecord.objects.filter(
                    course=course,
                    active=True,
                    deleted_at__isnull=True
                ).count()
                if active_registration_count is None:
                    return Response({"error": "Course Registration not found"}, status=status.HTTP_404_NOT_FOUND)
                course_active_registration_counts.append({
                    'course_id': course.id,
                    'course_title': course.title,
                    'active_registration_count': active_registration_count
                })
                
            return Response(course_active_registration_counts, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GraphOfProgressPerCourseView(APIView):
    """
    GET API for super admin to get count of completed, in progress and not-tarted status of courses separately.
    """
    permission_classes = [SuperAdminPermission]
    
    def get(self, request):
        try:
            active_courses = Course.objects.filter(active=True, deleted_at__isnull=True)
            if not active_courses:
                return Response({"message": "no active course found"},status=status.HTTP_404_NOT_FOUND)

            course_progress_counts = []
            for course in active_courses:
                completion_count = CourseCompletionStatusPerUser.objects.filter(
                    course=course,
                    active=True,
                    status='COMPLETED'
                ).count()
                in_progress_count = CourseCompletionStatusPerUser.objects.filter(
                    course=course,
                    active=True,
                    status='IN_PROGRESS'
                ).count()
                not_started_count = CourseCompletionStatusPerUser.objects.filter(
                    course=course,
                    active=True,
                    status='NOT_STARTED'
                ).count()
                course_progress_counts.append({
                    'course_id': course.id,
                    'course_title': course.title,
                    'completion_count': completion_count,
                    'course_in_progress_count': in_progress_count,
                    'course_not_started_count': not_started_count
                })
            return Response(course_progress_counts, status=status.HTTP_200_OK)
        except Exception as e:
            if isinstance(e, (CourseCompletionStatusPerUser.DoesNotExist)):
                return Response({"error": "Course Completion Status not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseCountView(APIView):
    """
    GET API for super admin to get count of active and inactive courses separately.
    """
    permission_classes = [SuperAdminPermission]
    
    def get(self, request):
        try:
            active_course_count = Course.objects.filter(active=True, deleted_at__isnull=True).count()
            inactive_course_count = Course.objects.filter(active=False, deleted_at__isnull=True).count()
            
            if active_course_count == 0:
                active_response = {"message": "No active courses were found"}
            else:
                active_serializer = ActiveCourseCountSerializer({'active_course_count': active_course_count})
                active_response = active_serializer.data
            if inactive_course_count == 0:
                inactive_response = {"message": "No inactive courses were found"}
            else:
                inactive_serializer = InActiveCourseCountSerializer({'inactive_course_count': inactive_course_count})
                inactive_response = inactive_serializer.data

            return Response({
                "active_courses": active_response,
                "inactive_courses": inactive_response
            }, status=status.HTTP_200_OK)
        except Exception as e:
            if isinstance(e, (ValidationError, Course.DoesNotExist)):
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
