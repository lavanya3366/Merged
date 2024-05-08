from rest_framework.views import APIView
from core.custom_permissions import CourseContentPermissions, SuperAdminOrGetOnly
from rest_framework import status
from django.core.files.base import ContentFile
import tempfile
from backend.models.allmodels import (
    Course,
    CourseRegisterRecord,
    UploadReadingMaterial,
    CourseStructure,
    CourseEnrollment,
    Quiz,
)
from backend.serializers.createcourseserializers import (
    CreateCourseStructureSerializer,
    CreateQuizSerializer,
    CreateUploadReadingMaterialSerializer,
)
from backend.serializers.courseserializers import (
    QuizSerializer,
)
from moviepy.editor import VideoFileClip # type: ignore
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from backend.serializers.courseserializers import *

import os
import subprocess
import boto3 # type: ignore
from botocore.exceptions import ClientError # type: ignore
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage  
from rest_framework import status
from django.conf import settings
import boto3 # type: ignore
from botocore.exceptions import ClientError,ValidationError # type: ignore
from backend.models.allmodels import *
from backend.models.coremodels import *
from backend.serializers.videocontentserializers import *
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
class UploadVideoToS3APIView(APIView):

    # permission_classes = [CourseContentPermissions]
    
    def post(self, request, course_id, *args, **kwargs):
        try:
            course = Course.objects.get(pk=course_id)
            if not course:
                return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            if course.active:
                return Response({"error": "Course is active, cannot proceed"}, status=status.HTTP_403_FORBIDDEN)

            serializer = UploadVideoSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            title = serializer.validated_data.get('title')
            video_file = serializer.validated_data.get('video')
            summary = serializer.validated_data.get('summary', '')
            
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in video_file.chunks():
                    temp_file.write(chunk)
            
                # Calculate video duration
                with VideoFileClip(temp_file.name) as video:
                    total_seconds = video.duration
                    minutes = int(total_seconds // 60)
                    seconds = int(total_seconds % 60)
                    video_duration = f"{minutes}.{seconds:02}"

            # Upload video file to S3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            s3_bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            s3_object_key = f"videos/{video_file.name}"

            s3_client.upload_fileobj(video_file, s3_bucket_name, s3_object_key)
            s3_client.put_object_acl(ACL='public-read', Bucket=s3_bucket_name, Key=s3_object_key)

            # Generate public URL
            public_video_url = f"https://{s3_bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_object_key}"

            
            
            # Save the public URL to the UploadVideo model
            upload_video = UploadVideo.objects.create(title=title, video=s3_object_key, url=public_video_url, summary=summary, video_duration=video_duration)
            course.video_materials.add(upload_video)
            
            # Create course structure entry if original_course is not null
            if course.original_course:
                last_order_number = UploadVideo.objects.filter(course=course).latest('order_number').order_number
                course_structure_data = {
                    'course': course_id,
                    'order_number': last_order_number + 1,
                    'content_type': 'video',
                    'content_id': upload_video.pk
                }
                course_structure_serializer = CreateCourseStructureSerializer(data=course_structure_data)
                if course_structure_serializer.is_valid():
                    course_structure_serializer.save()
                else:
                    return Response({"error": course_structure_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'success': True, 'public_video_url': public_video_url, 'id': upload_video.id, 'video_duration': video_duration}, status=status.HTTP_201_CREATED)
        
        except ClientError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request, course_id, format=None):
        try:
            content_id = request.query_params.get('content_id')
            count_calculator = request.query_params.get('count_calculator', '').lower() == 'true'
            list_mode = request.query_params.get('list', '').lower() == 'true'

            if count_calculator:
                if course_id:
                    video_material_count = UploadVideo.objects.filter(courses__id=course_id, active=True, deleted_at__isnull=True).count()
                    if video_material_count is None:
                        return Response({"message": "No video material found"}, status=status.HTTP_404_NOT_FOUND)
                    serializer = VideoMaterialCountPerCourseSerializer({'video_material_count': video_material_count})
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "No course id was passed in parameters"}, status=status.HTTP_400_BAD_REQUEST)

            if content_id:
                video_material = UploadVideo.objects.get(
                    courses__id=course_id, 
                    id=content_id, 
                    active=True, 
                    deleted_at__isnull=True
                )
                if video_material:
                    serializer = VideoMaterialSerializer(video_material)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Video material not found."}, status=status.HTTP_404_NOT_FOUND)

            elif list_mode:
                video_materials = UploadVideo.objects.filter(
                    courses__id=course_id, 
                    active=True, 
                    deleted_at__isnull=True
                )
                serializer = VideoMaterialListPerCourseSerializer(video_materials, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

            else:
                return Response({"error": "Specify 'content_id' or enable 'list' mode in query parameters."}, status=status.HTTP_400_BAD_REQUEST)

        except UploadVideo.DoesNotExist:
            return Response({"error": "Video material not found."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            if isinstance(e, ValidationError):
                return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
               
    
    def put(self, request, course_id, *args, **kwargs):
        try:
            content_id = request.query_params.get('content_id')
        
            if content_id is None:
                return Response({"error": "content_id is required in the query parameters."},
                            status=status.HTTP_400_BAD_REQUEST)
        
            with transaction.atomic():
            # Get the video material instance
                video_material = get_object_or_404(UploadVideo, pk=content_id)
            
            # Check if the associated course is active
                if video_material.courses.filter(pk=course_id, active=True).exists():
                    return Response({"error": "Cannot edit video material. Course is active."},
                                status=status.HTTP_403_FORBIDDEN)

            # Validate request data
                serializer = UploadVideoSerializer(instance=video_material, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)

            # Extract title, video file, and summary from validated data
                title = serializer.validated_data.get('title')
                video_file = serializer.validated_data.get('video')
                summary = serializer.validated_data.get('summary', '')
                
                
                
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    for chunk in video_file.chunks():
                        temp_file.write(chunk)
            
                # Calculate video duration
                    with VideoFileClip(temp_file.name) as video:
                        total_seconds = video.duration
                        minutes = int(total_seconds // 60)
                        seconds = int(total_seconds % 60)
                        video_duration = f"{minutes}.{seconds:02}"
                
            # Update video duration field
                video_material.video_duration = video_duration

            # Upload video file to AWS S3
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )

                s3_bucket_name = settings.AWS_STORAGE_BUCKET_NAME
                s3_object_key = f"videos/{video_file.name}"

                s3_client.upload_fileobj(video_file, s3_bucket_name, s3_object_key)
                s3_client.put_object_acl(ACL='public-read', Bucket=s3_bucket_name, Key=s3_object_key)

            # Generate public URL
                public_video_url = f"https://{s3_bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_object_key}"

            # Update video fields
                video_material.title = title
                video_material.video = s3_object_key
                video_material.url = public_video_url
                video_material.summary = summary
                video_material.video_duration = video_duration

            # Update course structure if needed
                edit_type = request.query_params.get('edit_type')
                if edit_type == 'status':
                    if video_material.active:
                        video_material.active = False
                        CourseStructure.objects.filter(content_id=content_id, content_type='video', active=True, deleted_at__isnull=True).update(active=False)
                    else:
                        video_material.active = True
                        try:
                            last_order_number = CourseStructure.objects.filter(course=course_id).latest('order_number').order_number
                        except CourseStructure.DoesNotExist:
                            last_order_number = 0
                        course_structure_data = {
                            'course': course_id,
                            'order_number': last_order_number + 1,
                            'content_type': 'video',
                            'content_id': video_material.pk
                        }
                        course_structure_serializer = CreateCourseStructureSerializer(data=course_structure_data)
                        if course_structure_serializer.is_valid():
                            course_structure_serializer.save()
                        else:
                            return Response({"error": course_structure_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            # Save the updated video material
                video_material.save()

            # Return success response with message and public URL
                return Response({'success': True, 'public_video_url': public_video_url}, status=status.HTTP_200_OK)

        except Exception as e:
            error_message = str(e)
            if isinstance(e, (UploadVideo.DoesNotExist, ValidationError)):
                error_message = "Video material not found." if isinstance(e, UploadVideo.DoesNotExist) else str(e)
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            return Response({"error": error_message}, status=status_code)       
    
    def patch(self, request, course_id, format=None):
        try:
            video_material_id = request.data.get('video_material_id')
            
            if video_material_id is None:
                return Response({"error": "video_material_id is required in the request body."},
                                status=status.HTTP_400_BAD_REQUEST)
            
            # Fetch the video material instance
            video_material = get_object_or_404(UploadVideo, pk=video_material_id)
            
            # Validate request data
            serializer = DeleteVideoMaterialSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                # Check if the video material is associated with other courses
                other_courses_count = video_material.courses.exclude(id=course_id).count()
                if other_courses_count > 0:
                    # Only remove the relation with the current course
                    video_material.courses.remove(course_id)
                else:
                    # No other courses are associated, soft delete the video material
                    video_material.deleted_at = timezone.now()
                    video_material.active = False
                    video_material.save()
                    
                    # Delete the course structure instance related to the video
                    CourseStructure.objects.filter(content_id=video_material_id, content_type='video', course_id=course_id).delete()
                
                return Response({"message": "Video material deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            error_message = str(e)
            if isinstance(e, (UploadVideo.DoesNotExist, ValidationError)):
                error_message = "Video material not found." if isinstance(e, UploadVideo.DoesNotExist) else str(e)
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            return Response({"error": error_message}, status=status_code)