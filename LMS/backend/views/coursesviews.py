from rest_framework import status
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from django.db import transaction
import pandas as pd

from core.custom_permissions import SuperAdminOrGetOnly, SuperAdminPermission
from backend.serializers.courseserializers import CourseDisplaySerializer
from backend.serializers.deletecourseserializers import(
    EditCourseInstanceSerializer,
    DeleteSelectedCourseSerializer
)
from backend.serializers.registercourseserializers import (
    DerivedVersionActiveCourseListSerializer, 
    FirstVersionActiveCourseListSerializer
)
from backend.models.allmodels import (
    ActivityLog,
    Course,
    Notification,
    UploadVideo,
    UploadReadingMaterial,
    CourseStructure,
    CourseEnrollment,
    Quiz,
)
from backend.serializers.createcourseserializers import (
    ActivateCourseSerializer,
    CourseSerializer, 
    # CourseStructureSerializer,
    InActivateCourseSerializer, 
    CreateCourseSerializer,
)
from backend.serializers.courseserializers import (
    CourseStructureSerializer,

)
from core.constants import filtered_display_list, manage_course_list


class CourseView(APIView):
    """
    GET API for super admin to list of courses or single instance based on query parameters passed
    
    POST API for super admin to create new instances of course
    """
    permission_classes = [SuperAdminOrGetOnly]

    def get(self, request, *args, **kwargs):
        try:
            course_id = request.query_params.get('course_id')
            filtered_display = request.query_params.get('filtered_display')

            if not course_id and not filtered_display:
                return Response({"error": "Course ID is missing from query parameters."}, status=status.HTTP_400_BAD_REQUEST)

            if course_id:
                course = Course.objects.get(pk=course_id)
                if not course:
                    return Response({"error": "No course found with the provided ID."}, status=status.HTTP_404_NOT_FOUND)
                if course.deleted_at:
                    return Response({"error": "Access to deleted course is not allowed."}, status=status.HTTP_403_FORBIDDEN)
                serializer = CourseSerializer(course)
                return Response(serializer.data, status=status.HTTP_200_OK)

            if filtered_display:
                if filtered_display not in filtered_display_list : #["active", "inactive", "all"]
                    return Response({"error": "Invalid filtered_display parameter"}, status=status.HTTP_400_BAD_REQUEST)
                
                queryset = Course.objects.filter(deleted_at__isnull=True).order_by('-created_at')
                
                if filtered_display == "active":
                    queryset = queryset.filter(active=True)
                elif filtered_display == "inactive":
                    queryset = queryset.filter(active=False)
                course_list = queryset.all()
                
                if not course_list.exists():
                    return Response({"message": "No course found.", "data": []}, status=status.HTTP_404_NOT_FOUND)
                serializer = CourseDisplaySerializer(course_list, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, *args, **kwargs):        
        try:
            data = request.data
            if not data:
                return Response({"error": "Request body is empty"}, status=status.HTTP_400_BAD_REQUEST)
            serializer = CreateCourseSerializer(data=data)
            if serializer.is_valid():
                serializer.validated_data['active'] = False
                serializer.validated_data['original_course'] = None
                serializer.validated_data['version_number'] = 1
                course = serializer.save()
                return Response({"message": "Course created successfully", "course_id": course.pk}, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def put(self, request, format=None):
        try:
            course_id = request.data.get('course_id')
            course = Course.objects.get(pk=course_id)
            
            if not course:
                raise Course.DoesNotExist("No course found with the provided course ID.")
            if course.deleted_at:
                raise ValidationError("Course instance has been deleted")
            
            serializer = EditCourseInstanceSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            course.title = serializer.validated_data.get('title')
            course.summary = serializer.validated_data.get('summary')
            course.updated_at = timezone.now()
            course.save()

            if course.active:
                latest_activity_log = ActivityLog.objects.latest('created_at')
                notification = Notification.objects.create(
                    message=latest_activity_log.message,
                    course=course
                )
                notification_data = {
                    "message": notification.message,
                    "created_at": notification.created_at
                }
                return Response({"message": "Course instance updated successfully", "notification": notification_data}, status=status.HTTP_200_OK)
            return Response({"message": "Course instance updated successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            error_message = str(e)
            if isinstance(e, (ValidationError, Course.DoesNotExist)):
                error_message = "Invalid data: " + error_message
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST) 


    def patch(self, request, format=None):
        try:
           
            serializer = DeleteSelectedCourseSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            course_id = serializer.validated_data['course_id']

            # Fetch the course instance
            course = Course.objects.get(id=course_id)

            # Check if the course is active
            if course.active:
                raise ValidationError("Course must be inactive before deletion.")

            # Soft delete the course
            course.active = False
            course.deleted_at = timezone.now()
            course.save()

            # Delete related instances if they are associated only with this course
            self.delete_related_instances(course)

            return Response({"message": "Course soft deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete_related_instances(self, course):
        # Delete mapped instances of course_id with reading material
        reading_materials = UploadReadingMaterial.objects.filter(courses=course)
        if reading_materials.exists():
            reading_materials.delete()

        # Delete mapped instances of course_id with video material
        video_materials = UploadVideo.objects.filter(courses=course)
        if video_materials.exists():
            video_materials.delete()

        # Delete mapped instances of course_id with quiz and associated questions
        quizzes = Quiz.objects.filter(courses=course)
        for quiz in quizzes:
            if quiz.questions.count() > 0:
                quiz.questions.all().delete()
            quiz.delete()
        


class ManageCourseView(APIView):
    """
    POST API for super admin to manage the instance of course according to passed parameter.
    
    activate : to activate inactive course
    
    inactivate : to inactivate active course
    
    versioning : to create a new version of existing active course
    """
    permission_classes = [SuperAdminPermission]
    
    def post(self, request, *args, **kwargs):
        try:
            manage = request.data.get('manage')
            
            if manage not in manage_course_list:
                return Response({"error": "Invalid manage_status in request"}, status=status.HTTP_400_BAD_REQUEST)
            course_id = request.data.get('course_id')
            if not course_id:
                return Response({"error": "Course ID is missing"}, status=status.HTTP_400_BAD_REQUEST)
            if manage == "activate":
                return self.activate_course(course_id)
            elif manage == "inactivate":
                return self.inactivate_course(course_id)
            elif manage == "versioning":
                return self.create_course_derived_version(course_id)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def activate_course(self, course_id):
        try:
            course = Course.objects.get(pk=course_id, deleted_at__isnull=True)
            if not course:
                return Response({"error":"no course found"},status=status.HTTP_404_NOT_FOUND)
            if course.active:
                return Response({"message": "Course is already active."}, status=status.HTTP_200_OK)
            serializer = ActivateCourseSerializer(data={'course_id': course.id})
            if serializer.is_valid():
                course = serializer.validated_data['course_id']
                if course.original_course is None:
                    course.active = True
                    course.save()
                    return Response({"message": "Course activated successfully."}, status=status.HTTP_200_OK)
                else:
                    original_course_structure = CourseStructure.objects.filter(course=course.original_course).values_list('content_type', 'content_id')
                    current_course_structure = CourseStructure.objects.filter(course=course).values_list('content_type', 'content_id')
                    if not original_course_structure or not current_course_structure:
                        return Response({"message":"Course Structure not found."}, status=status.HTTP_404_NOT_FOUND)

                    original_course_structure_df = pd.DataFrame(original_course_structure, columns=['content_type', 'content_id'])
                    current_course_structure_df = pd.DataFrame(current_course_structure, columns=['content_type', 'content_id'])

                    if original_course_structure_df.equals(current_course_structure_df):
                        return Response({"error": "Cannot activate the course. Course structure have exact match with original course."},
                                        status=status.HTTP_400_BAD_REQUEST)
                    else:
                        course.active = True
                        course.save()
                        return Response({"message": "Course activated successfully."}, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def inactivate_course(self, course_id):
        try:
            course = Course.objects.get(pk=course_id, deleted_at__isnull=True)
            if not course:
                return Response({"error":"no course found"},status=status.HTTP_404_NOT_FOUND)
            if not course.active:
                return Response({"message": "Course is already inactive."}, status=status.HTTP_200_OK)
            serializer = InActivateCourseSerializer(data={'course_id': course_id})
            if serializer.is_valid():
                course = serializer.validated_data['course_id']
                active_enrollments_count = CourseEnrollment.objects.filter(course=course, active=True, deleted_at__isnull=True).count()
                if active_enrollments_count is None :
                    return Response({"error":"no active course enrollment found"},status=status.HTTP_404_NOT_FOUND)
                course.active = False
                course.save()
                return Response({"message": "Course inactivated successfully.",
                                "active_enrollments_before_inactivation": active_enrollments_count},
                                status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
    def create_course_derived_version(self, course_id):
        try:
            original_course = Course.objects.get(pk=course_id)
            if not original_course.active:
                return Response({"error": "The original course is not active"}, status=status.HTTP_400_BAD_REQUEST)
            inactive_versions_count = Course.objects.filter(Q(original_course=original_course) & Q(active=False, deleted_at__isnull=True)).count()
            if inactive_versions_count >= 2:
                return Response(
                    {"error": "Two or more inactive versions of this course already exist. Delete or activate them first."},
                    status=status.HTTP_400_BAD_REQUEST)
        except Course.DoesNotExist:
            return Response({"error": "Original course not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            with transaction.atomic():
                # Create new course instance based on original course
                new_course_data = {
                    'title': original_course.title,
                    'summary': original_course.summary,
                    'active': False,
                    'original_course': original_course.id,
                    'created_at': timezone.now(),
                    'updated_at': timezone.now(),
                    'version_number': Course.objects.filter(original_course=original_course).count() + 2
                }
                new_course_serializer = CourseSerializer(data=new_course_data)
                if new_course_serializer.is_valid():
                    new_course = new_course_serializer.save()
                else:
                    return Response({"error": new_course_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                
                # Copy course structure from original course
                original_course_structure = CourseStructure.objects.filter(course=original_course)
                if not original_course_structure:
                    return Response({"error": "The original course structure not found"}, status=status.HTTP_404_NOT_FOUND)
                for structure in original_course_structure:
                    structure_data = CourseStructureSerializer(structure).data
                    structure_data['course'] = new_course.pk
                    structure_serializer = CourseStructureSerializer(data=structure_data)
                    if structure_serializer.is_valid():
                        structure_serializer.save()
                    else:
                        return Response({"error": structure_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                
                related_reading_materials = UploadReadingMaterial.objects.filter(courses=original_course)
                if related_reading_materials:
                    new_course.reading_materials.set(related_reading_materials)
                    
                # Map existing UploadVideo
                related_videos = UploadVideo.objects.filter(courses=original_course)
                if related_videos:
                    new_course.video_materials.set(related_videos)
                    
                # Map existing Quiz
                related_quizzes = Quiz.objects.filter(courses=original_course)
                if related_quizzes:
                    new_course.quizzes.set(related_quizzes)
            return Response({"message": "New version of course created successfully."}, status=status.HTTP_201_CREATED)
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FirstVersionActiveCourseListView(APIView):
    """
    GET API for super admin to list of courses with original_course == null and version == 1
    """
    permission_classes = [SuperAdminPermission]
    
    def get(self, request):
        try:
            courses = Course.objects.filter(original_course__isnull=True, version_number=1, active=True).order_by('-updated_at')
            if not courses:
                return Response({"error": "No active first version courses found."}, status=status.HTTP_404_NOT_FOUND)
            serializer = FirstVersionActiveCourseListSerializer(courses, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DerivedVersionActiveCourseListView(APIView):
    """
    GET API for super admin to list of courses with original_course != null and version != 1 for course in url
    """
    permission_classes = [SuperAdminPermission] 
    
    def get(self, request, course_id):
        try:
            derived_courses = Course.objects.filter(original_course=course_id, active=True).order_by('version_number','-updated_at')
            if not derived_courses:
                return Response({"error": "No active derived courses found for the provided course ID."}, status=status.HTTP_404_NOT_FOUND)
            serializer = DerivedVersionActiveCourseListSerializer(derived_courses, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)