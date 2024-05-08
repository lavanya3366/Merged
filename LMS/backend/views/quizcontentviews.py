from datetime import timezone
import json
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from core.custom_permissions import SuperAdminPermission
from backend.serializers.deletecourseserializers import  DeleteChoiceSerializer
from backend.serializers.editserializers import EditingQuestionInstanceOnConfirmationSerializer
from django.core.exceptions import ObjectDoesNotExist
from core.custom_mixins import (
    SuperAdminMixin)
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from rest_framework import status
from django.contrib import messages
from backend.serializers.courseserializers import (
    DeleteQuestionSerializer,
    EditQuestionInstanceSerializer
)
from backend.models.allmodels import (
    Choice,
    Course,
    CourseStructure,
    Progress,
    Quiz,
    Question,
    QuizAttemptHistory,
)
from backend.serializers.createcourseserializers import (
    # CourseStructureSerializer,
    CreateChoiceSerializer,
    CreateQuestionSerializer,
    QuizSerializer, 
)
from django.db import transaction
from backend.serializers.courseserializers import (
    CourseStructureSerializer,

)
import pandas as pd
from backend.forms import (
    QuestionForm,
)
from backend.models.coremodels import *
from backend.serializers.courseserializers import *
from rest_framework.response import Response
from django.views.generic import (
    FormView,
)
from backend.forms import (
    QuestionForm,
)

class QuestionView(APIView):
    """
    GET API for super admin to list of questions of specific quiz
    
    POST API for super admin to create new instances of question for the quiz
    
    """
    permission_classes = [SuperAdminPermission]
    
    def get(self, request,course_id, quiz_id, format=None):
        try:
            questions = Question.objects.filter(
                quizzes__id=quiz_id, 
                active=True, 
                deleted_at__isnull=True
            ).order_by('created_at')
            serializer = QuestionListPerQuizSerializer(questions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, course_id, quiz_id, *args, **kwargs):
        course = Course.objects.get(pk=course_id)
        if not course:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        if course.active:
            return Response({"error": "Course is active, cannot proceed"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        if not data:
            return Response({"error": "Request body is empty"}, status=status.HTTP_400_BAD_REQUEST)
        # Check if the quiz is related to other courses
        related_courses_count = Quiz.objects.exclude(courses__pk=course_id).filter(pk=quiz_id).count()
        if related_courses_count is None:
            return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            
            if related_courses_count > 0:
            # Create a new instance of quiz and add the question
                new_quiz = self.create_new_quiz_instance(course_id, quiz_id, data)
                if new_quiz is not None:
                    # Update the quiz_id in the course structure
                    self.update_course_structure(course_id,quiz_id, new_quiz.id)
                    return Response({"message": "Question created successfully"}, status=status.HTTP_201_CREATED)
                else:
                    return Response({"error": "Failed to create new quiz instance"}, status=status.HTTP_400_BAD_REQUEST)
            else:
            # Add the question to the existing quiz
                serializer = CreateQuestionSerializer(data=data)
                if serializer.is_valid():
                    serializer.save(quizzes=[quiz_id])
                    return Response({"message": "Question created successfully"}, status=status.HTTP_201_CREATED)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_new_quiz_instance(self, course_id, quiz_id, data):
        try:
            with transaction.atomic():
                # Retrieve the existing quiz
                existing_quiz = Quiz.objects.get(pk=quiz_id)

                # Create a new instance of quiz with the same data
                new_quiz = Quiz.objects.create(
                    title=existing_quiz.title,
                    description=existing_quiz.description,
                    answers_at_end=existing_quiz.answers_at_end,
                    exam_paper=existing_quiz.exam_paper,
                    single_attempt=existing_quiz.single_attempt,
                    pass_mark=existing_quiz.pass_mark
                )
                new_quiz.courses.set([course_id])
                
                related_questions = existing_quiz.questions.all()
                new_quiz.questions.set(related_questions)

                serializer = CreateQuestionSerializer(data=data)
                if serializer.is_valid():
                    serializer.save(quizzes=[new_quiz.pk])
                    return new_quiz
                else:
                    new_quiz.delete()  # Rollback if question creation fails
                    return None
        except Quiz.DoesNotExist:
            return None

    def update_course_structure(self, course_id, old_quiz_id, new_quiz_id):
        try:
            # Update CourseStructure entries with the new quiz id
            CourseStructure.objects.filter(course=course_id ,content_type='quiz',content_id=old_quiz_id ).update(content_id=new_quiz_id)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def put(self, request, course_id, quiz_id, format=None):  
        error_response = None
        try:
            # Extract question_id from request body
            question_id = request.data.get('question_id')
            if not question_id:
                raise ValidationError("Question ID is required in the request body.")

            # Check if quiz exists
            quiz = Quiz.objects.get(pk=quiz_id)

            # Check if question exists
            question = Question.objects.get(pk=question_id)
            if quiz not in question.quizzes.all():
                raise ValidationError("Question not found for the specified quiz.")

            # Check if course exists
            course = Course.objects.get(pk=course_id)
            if course.active:
                error_response = {"error": "Editing is not allowed for active courses."}
            elif course not in quiz.courses.all():
                error_response = {"error": "Quiz not found for the specified course."}
            else:
                # Update question instance
                serializer = EditQuestionInstanceSerializer(question, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)

        except ValidationError as e:
            error_response = {"error": str(e)}
        
        if error_response:
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)

        # Handle other unexpected errors
        return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def patch(self, request, course_id, quiz_id, format=None):
        error_response = None
        try:
            # Validate request data
            serializer = DeleteQuestionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Extract validated question_id
            question_id = serializer.validated_data['question_id']
            
            # Fetch the question instance
            question = Question.objects.get(id=question_id)

            # Check if the question is associated with the specified quiz
            if quiz_id not in question.quizzes.values_list('id', flat=True):
                error_response = {"error": "Question not found for the specified quiz."}
            else:
                # Check if the question is associated with other quizzes
                other_quizzes_count = question.quizzes.exclude(id=quiz_id).count()
                if other_quizzes_count > 0:
                    # Only remove the relation with the current quiz
                    question.quizzes.remove(quiz_id)
                else:
                    # No other quizzes are associated, soft delete the question
                    question.deleted_at = timezone.now()
                    question.active = False
                    question.save()

                return Response({"message": "Question deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

        except ObjectDoesNotExist:
            error_response = {"error": "Question not found."}

        if error_response:
            return Response(error_response, status=status.HTTP_404_NOT_FOUND)

        # Handle other unexpected errors
        return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChoicesView(APIView):
    """
    GET API for super admin to list of choices of specific question
    
    POST API for super admin to create new instances of choice for the question
    
    """
    permission_classes = [SuperAdminPermission] 
    
    def get(self, request, question_id, format=None):
        try:
            choices = Choice.objects.filter(
                question__id=question_id, 
                active=True, 
                deleted_at__isnull=True
            ).order_by('created_at')
            serializer = ChoicesListPerQuestionSerializer(choices, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, question_id, *args, **kwargs):
        question = Question.objects.get(pk=question_id)
        if not question:
            return  Response({"error": "Question not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            serializer = CreateChoiceSerializer(data=request.data, context={'question_id': question_id})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
                if isinstance(e, ValidationError):
                    return Response({"error": "Validation Error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def patch(self, request, question_id):
        try:
            serializer = DeleteChoiceSerializer(data=request.query_params)
            serializer.is_valid(raise_exception=True)
            choice_id = serializer.validated_data.get('choice_id')
            choice = Choice.objects.get(id=choice_id, question_id=question_id)
            # Check if the choice instance has already been soft deleted
            if choice.deleted_at:
                return Response({'error': 'Choice already soft deleted'}, status=status.HTTP_400_BAD_REQUEST)
            # Soft delete the choice instance by marking it as deleted
            choice.deleted_at = timezone.now()
            choice.active = False
            choice.save()
            # Return success response
            return Response({'message': 'Choice soft deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            error_message = 'Course structure not found'
            if isinstance(e, serializers.ValidationError):
                error_message = e.detail
                status_code = status.HTTP_400_BAD_REQUEST
            else:
                status_code = status.HTTP_404_NOT_FOUND
            return Response({'error': error_message}, status=status_code)


# @method_decorator([login_required], name="dispatch")
class QuizTake(FormView):
    form_class = QuestionForm
    template_name = "question.html"
    result_template_name = "result.html"

    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz, slug=self.kwargs["quiz_slug"])
        self.course = get_object_or_404(Course, pk=self.kwargs["pk"])
        quiz_questions_count = self.quiz.questions.count()
        course = get_object_or_404(Course, pk=self.kwargs["pk"])

        if quiz_questions_count <= 0:
            messages.warning(request, f"Question set of the quiz is empty. try later!")
            return redirect("course-structure", self.course.id) # redirecting to previous page as this quiz can't be started.
        # =================================================================
        # user = request.data.get('user')
        user = {
            "id": 11,
            "first_name": "John",
            "last_name": "Doe",
            "role": 1,
            "email": "john.doe@example.com",
            "password": "password123",
            "access_token": "abc123xyz",
            "status": "active",
            "created_by_id": 1,
            "customer": 1,
            "user_role_id": 2
        }
        user_id = user['id']
        enrolled_user = get_object_or_404(User, pk=user_id)
        # ===============================
        # enrolled_user = request.user
        # ===============================

        self.sitting = QuizAttemptHistory.objects.user_sitting(
            enrolled_user,
            self.quiz, 
            self.course
        )

        if self.sitting is False:
            messages.info(
                request,
                f"You have already sat this exam and only one sitting is permitted",
            )
            return redirect("course-structure", self.course.id)

        return super(QuizTake, self).dispatch(request, *args, **kwargs)

    def get_form(self, *args, **kwargs):
        self.question = self.sitting.get_first_question()
        self.progress = self.sitting.progress()
        form_class = self.form_class

        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        kwargs = super(QuizTake, self).get_form_kwargs()

        return dict(kwargs, question=self.question)

    def form_valid(self, form):
        self.form_valid_user(form)
        if self.sitting.get_first_question() is False:
            self.sitting.mark_quiz_complete()
            return self.final_result_user()

        self.request.POST = {}

        return super(QuizTake, self).get(self, self.request)

    def get_context_data(self, **kwargs):
        context = super(QuizTake, self).get_context_data(**kwargs)
        context["question"] = self.question
        context["quiz"] = self.quiz
        context["course"] = get_object_or_404(Course, pk=self.kwargs["pk"])
        if hasattr(self, "previous"):
            context["previous"] = self.previous
        if hasattr(self, "progress"):
            context["progress"] = self.progress
        return context

    def form_valid_user(self, form):
        # =================================================================
        # user = self.request.data.get('user')
        user = {
            "id": 11,
            "first_name": "John",
            "last_name": "Doe",
            "role": 1,
            "email": "john.doe@example.com",
            "password": "password123",
            "access_token": "abc123xyz",
            "status": "active",
            "created_by_id": 1,
            "customer": 1,
            "user_role_id": 2
        }
        user_id = user['id']
        enrolled_user = get_object_or_404(User, pk=user_id)
        # ===============================
        # enrolled_user = request.user
        # ===============================

        progress, _ = Progress.objects.get_or_create(enrolled_user=enrolled_user)
        guess = form.cleaned_data["answers"]
        is_correct = self.question.check_if_correct(guess)

        if is_correct is True:
            self.sitting.add_to_score(1)
            progress.update_score(self.question, 1, 1)
        else:
            self.sitting.add_incorrect_question(self.question)
            progress.update_score(self.question, 0, 1)

        if self.quiz.answers_at_end is not True:
            self.previous = {
                "previous_answer": guess,
                "previous_outcome": is_correct,
                "previous_question": self.question,
                "answers": self.question.get_choices(),
                "question_type": {self.question.__class__.__name__: True},
            }
        else:
            self.previous = {}

        self.sitting.add_user_answer(self.question, guess)
        self.sitting.remove_first_question()

    def final_result_user(self):
        results = {
            "course": get_object_or_404(Course, pk=self.kwargs["pk"]),
            "quiz": self.quiz,
            "score": self.sitting.get_current_score,
            "max_score": self.sitting.get_max_score,
            "percent": self.sitting.get_percent_correct,
            "sitting": self.sitting,
            "previous": self.previous,
            "course": get_object_or_404(Course, pk=self.kwargs["pk"]),
        }

        self.sitting.mark_quiz_complete()

        if self.quiz.answers_at_end:
            results["questions"] = self.sitting.get_questions(with_answers=True)
            results["incorrect_questions"] = self.sitting.get_incorrect_questions

        if (
            self.quiz.exam_paper is False
        ):
            self.sitting.delete()

        return render(self.request, self.result_template_name, results)

# def dummy_quiz_index(request, course_id):
#     course = Course.objects.get(pk=course_id)
#     return render(request, 'quiz_index.html', {'course_id': course_id, 'course': course})

class EditingQuestionInstanceOnConfirmationView(APIView):
    
    """ 
    PUT API : for editing question if the confirmation is true then editing allowed
    
    """
    permission_classes = [SuperAdminPermission]
    def put(self, request, course_id, quiz_id, format=None):
        try:
            serializer = EditingQuestionInstanceOnConfirmationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            confirmation = serializer.validated_data['confirmation']
            quiz = Quiz.objects.get(pk=quiz_id)
            questions = quiz.questions.all()
            
            if confirmation:
                # Editing existing question instances
                for question in questions:
                    question.figure = serializer.validated_data.get('figure', question.figure)
                    if 'content' in serializer.validated_data and serializer.validated_data['content'] is not None:
                        question.content = serializer.validated_data['content']
                    question.explanation = serializer.validated_data.get('explanation', question.explanation)
                    question.choice_order = serializer.validated_data.get('choice_order', question.choice_order)
                    question.updated_at = timezone.now()
                    question.save()
                
                return Response({"message": "Question instances updated successfully."}, status=status.HTTP_200_OK)
            else:
                # Do not allow updating, suggest creating a new question
                return Response({"message": "You chose not to update existing questions. Please create new ones instead."},
                                status=status.HTTP_400_BAD_REQUEST)
        
        except (Quiz.DoesNotExist, Exception) as e:
            if isinstance(e, Quiz.DoesNotExist):
                return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
