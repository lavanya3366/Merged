from django.db import transaction
from django.db.models import  Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from core.custom_permissions import ClientAdminPermission, SuperAdminOrPostOnly
from backend.serializers.scoreserializers import CourseCompletionStatusSerializer
from backend.models.allmodels import (
    CourseCompletionStatusPerUser,
    CourseStructure,
    QuizAttemptHistory,
    QuizScore,
)
from backend.serializers.scoreserializers import QuizScoreSerializer
from backend.models.allmodels import CourseEnrollment

class CourseCompletionStatusView(APIView):
    """
    creation of new instance  course completion status instance
    allowed for client admin
    POST request
    triggered after course enrollment records creation, similar to that one.
    in request body:
        list of course_id =[..., ..., ..., ...]
        list of user_id =[..., ..., ..., ...]
        each course in list will be mapped for all users in list
    while creating instance:
        enrolled_user = request body
        course = request body
        status = (default='not started')
        created_at = (auto_now_add=True)
    """
    permission_classes = [ClientAdminPermission]

    def post(self, request):
        try:
            course_ids = request.data.get('course_id', [])
            user_ids = request.data.get('user_id', [])

            if not course_ids or not user_ids:
                return Response({'error': 'course_id and user_id lists are required'}, status=status.HTTP_400_BAD_REQUEST)

            course_completion_statuses = []
            for course_id in course_ids:
                for user_id in user_ids:
                    # Check if the user is enrolled in the course
                    if not CourseEnrollment.objects.filter(course_id=course_id, user_id=user_id).exists():
                        return Response({'error': 'course enrollment not found'}, status=status.HTTP_404_NOT_FOUND)

                    existing_entry = CourseCompletionStatusPerUser.objects.filter(course_id=course_id, enrolled_user_id=user_id).first()
                    if existing_entry:
                        return Response({'error': 'instance already exists'}, status=status.HTTP_200_OK)


                    course_completion_status = CourseCompletionStatusPerUser(
                        enrolled_user_id=user_id,
                        course_id=course_id,
                        created_at=timezone.now(),
                        updated_at=timezone.now(),
                        active=True,
                        status="not_started"
                    )
                    course_completion_statuses.append(course_completion_status)

            CourseCompletionStatusPerUser.objects.bulk_create(course_completion_statuses)

            serializer = CourseCompletionStatusSerializer(course_completion_statuses, many=True)
            return Response({'message': 'course completion status created successfully', 'completion_status': serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        

class QuizScoreView(APIView):
    """
    creation of new instance of quiz score
    allowed for client admin
    POST request
    triggered after course enrollment records creation, similar to that one.
    in request body:
        list of course_id =[..., ..., ..., ...]
        list of user_id =[..., ..., ..., ...]
        each course in list will be mapped for all users in list
    while creating instance:
        enrolled_user = request body
        course = request body
        total_quizzes_per_course = calculate in view for course by counting active quizzes in it
        completed_quiz_count = by default 0
        total_score_per_course = (default=0)
    """
    permission_classes = [ClientAdminPermission]
    
    def post(self, request):
        try:
            course_ids = request.data.get('course_id', [])
            user_ids = request.data.get('user_id', [])

            if not course_ids or not user_ids:
                return Response({'error': 'course_id and user_id lists are required'}, status=status.HTTP_400_BAD_REQUEST)

            quiz_scores = []
            for course_id in course_ids:
                total_quizzes_per_course = self.get_total_quizzes_per_course(course_id)

                for user_id in user_ids:
                    if not CourseEnrollment.objects.filter(course_id=course_id, user_id=user_id).exists():
                         return Response({'error': 'course enrollment not found'}, status=status.HTTP_404_NOT_FOUND)

                    existing_score = QuizScore.objects.filter(course_id=course_id, enrolled_user_id=user_id).first()

                    if existing_score:
                        return Response({'message': 'this quiz score already exists '}, status=status.HTTP_200_OK)

                    quiz_score = QuizScore(
                        enrolled_user_id=user_id,
                        course_id=course_id,
                        total_quizzes_per_course=total_quizzes_per_course,
                        completed_quiz_count=0,
                        total_score_per_course=0,
                        created_at=timezone.now(),
                        updated_at=timezone.now(),
                        active=True
                    )
                    quiz_scores.append(quiz_score)

            QuizScore.objects.bulk_create(quiz_scores)

            serializer = QuizScoreSerializer(quiz_scores, many=True)
            return Response({'message': 'quiz score created successfully', 'quiz_score': serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_total_quizzes_per_course(self, course_id):
        try:
            total_quizzes = CourseStructure.objects.filter(course_id=course_id, content_type='quiz', active=True, deleted_at__isnull=True).count()
            return total_quizzes
        except Exception as e:
            return 0


class QuizScorePerCourseView(APIView):
    """
    POST request
    triggered after quiz attempt history for a course, where user has completed = true.
    Update metrics including completed_quiz_count and total_score_per_course.
    """
    permission_classes = [SuperAdminOrPostOnly]

    def post(self, request):
        try:
            course_ids = request.data.get('course_id', [])
            user_ids = request.data.get('user_id', [])

            if not (course_ids and user_ids):
                return Response({'error': 'course_id and user_id lists are required'}, status=status.HTTP_400_BAD_REQUEST)

            for course_id in course_ids:
                for user_id in user_ids:
                    if not (course_id and user_id):
                        return Response({'error': 'course_id and user_id are required'}, status=status.HTTP_400_BAD_REQUEST)

                    # Count distinct completed quizzes for the user and course
                    completed_quizzes_count = QuizAttemptHistory.objects.filter(course_id=course_id, enrolled_user_id=user_id, complete=True).values('quiz_id').distinct().count()

                    # Calculate total score for the course
                    last_attempted_quizzes = (
                        QuizAttemptHistory.objects.filter(course_id=course_id, enrolled_user_id=user_id, complete=True)
                        .values('quiz_id')
                        .annotate(last_attempt=Max('created_at'))
                        .order_by('-last_attempt')
                    )

                    unique_quizzes = QuizAttemptHistory.objects.filter(
                        course_id=course_id,
                        enrolled_user_id=user_id,
                        complete=True,
                        created_at__in=[quiz['last_attempt'] for quiz in last_attempted_quizzes]
                    )

                    total_score = 0
                    for quiz_attempt in unique_quizzes:
                        total_score += (quiz_attempt.current_score / (len(quiz_attempt.question_list_order.split(','))-1))

                    total_quizzes = CourseStructure.objects.filter(course_id=course_id, content_type='quiz', active=True).count()

                    if total_quizzes > 0:
                        average_score = (total_score / total_quizzes) * 100.0
                    else:
                        average_score = 0

                    # Update or create QuizScore object
                    quiz_score, created = QuizScore.objects.get_or_create(
                        course_id=course_id,
                        enrolled_user_id=user_id,
                        defaults={'completed_quiz_count': 0, 'total_score_per_course': 0}
                    )

                    quiz_score.completed_quiz_count = completed_quizzes_count
                    quiz_score.total_score_per_course = average_score
                    quiz_score.total_quizzes_per_course=total_quizzes
                    quiz_score.save()

            # Serialize the QuizScore objects
            quiz_scores = QuizScore.objects.filter(course_id__in=course_ids, enrolled_user_id__in=user_ids)
            serializer = QuizScoreSerializer(quiz_scores, many=True)
            return Response({'message': 'Quiz scores per course updated successfully', 'quiz_score_per_course': serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class CourseCompletionStatusPerUserView(APIView):
    """
    POST request triggered when 
    total_quizzes_per_course = completed_quiz_count in quiz score for that user in request
    if total_quizzes_per_course == completed_quiz_count:
        completion_status=True and in_progress_status =False
    if total_quizzes_per_course > completed_quiz_count:
        completion_status=False and in_progress_status =True
    """
    permission_classes = [SuperAdminOrPostOnly]

    @transaction.atomic
    def post(self, request):
        try:
            course_ids = request.data.get('course_id', [])
            user_ids = request.data.get('user_id', [])

            if not (course_ids and user_ids):
                return Response({'error': 'course_id and user_id are required'}, status=status.HTTP_400_BAD_REQUEST)

            for course_id in course_ids:
                for user_id in user_ids:

                    course_completion_status, created = CourseCompletionStatusPerUser.objects.get_or_create(
                        course_id=course_id, enrolled_user_id=user_id
                    )

                    quiz_score = get_object_or_404(QuizScore, course_id=course_id, enrolled_user_id=user_id)

                    if quiz_score.total_quizzes_per_course == quiz_score.completed_quiz_count:
                        course_completion_status.status = "completed"
                        
                    elif quiz_score.total_quizzes_per_course > quiz_score.completed_quiz_count:
                        course_completion_status.status = "in_progress"
                    else:
                        course_completion_status.status = "not_started"

                    course_completion_status.save()

                    # Serialize the updated course completion status
                    serializer = CourseCompletionStatusSerializer(course_completion_status)
                    return Response({'message': 'Course completion status updated successfully', 'course_completion_status': serializer.data}, status=status.HTTP_200_OK)
        
        except Exception as e:
            if isinstance(e, QuizScore.DoesNotExist):
                return Response({'error': 'Quiz score record not found'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)