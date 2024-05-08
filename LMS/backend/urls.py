from django.contrib import admin
from django.urls import path

from core.custom_permissions import SuperAdminPermission
from rest_framework.permissions import IsAuthenticated
from .views.videocontentviews import *

# from .views.coursemanagementviews import (# )
# from .views.courseviews import (# )

from .views.superadmindashboardviews import (
    ActiveRegisteredCustomerCountView,
    CountOfActiveRegistrationPerCoure, 
    CourseCountView,
    GraphOfProgressPerCourseView, 
)

from .views.clientdashboardviews import (
    CountCoursesStatusView,
    DisplayClientCourseProgressView,
)
from .views.clientadmindashboard import(
    ProgressCountView,
    RegisteredCourseCountView, 
    ActiveEnrolledUserCountPerCustomerView,
    
) 

from .views.scoreviews import (
    CourseCompletionStatusView,
    QuizScoreView,
    QuizScorePerCourseView,
    CourseCompletionStatusPerUserView,
)

from .views.registercourseviews import (
    CourseCustomerRegistrationView,
    LMSCustomerListView,
    ManageCourseRegistrationRecordStatusView
)
from .views.coursesviews import (
    CourseView,
    ManageCourseView,
    FirstVersionActiveCourseListView,
    DerivedVersionActiveCourseListView,
)
from .views.coursecontentviews import (
    CourseStructureView,
    ReadingMaterialView,
    QuizView,
    EditQuizInstanceOnConfirmationView,
    NotificationBasedOnCourseDisplayView)

from .views.quizcontentviews import (
    ChoicesView,
    EditingQuestionInstanceOnConfirmationView,
    QuestionView,
    QuizTake,
)
from .views.enrollcourseviews import( 
   CourseEnrollmentView,
    DisplayCourseListView,
    UserListForEnrollmentView,
    ManageCourseEnrollmentView
    )
urlpatterns = [
    #registercourseviews.py views url
    path('lms-customer/', LMSCustomerListView.as_view(), name='lms-customer-list'), #0
    path('course-register-record/', CourseCustomerRegistrationView.as_view(), name='course-register-record'), #1
    path('manage-status/register-records/', ManageCourseRegistrationRecordStatusView.as_view(), name='manage-register-records'),  #2
    
    # coursesviews.py view urls
    path('courses/', CourseView.as_view(), name='courses'), #3
    path('manage/course/', ManageCourseView.as_view(), name='manage-course'), #4
    path('courses/active/v1/', FirstVersionActiveCourseListView.as_view(), name='active-first-version-courses-list'),  #5
    path('courses/derived-active/<int:course_id>/', DerivedVersionActiveCourseListView.as_view(), name='active-derived-version-course-list'),  #6
    
    # coursecontentviews.py view urls
    path('course/<int:course_id>/structure/', CourseStructureView.as_view(), name='course-structure'), #7
    path('course/<int:course_id>/reading-material/', ReadingMaterialView.as_view(), name='reading-material'), #8
    path('course/<int:course_id>/quiz/', QuizView.as_view(), name='quiz'), #9
    
    # quizcontentviews.py views urls
    path('course/<int:course_id>/quiz/<int:quiz_id>/question/', QuestionView.as_view(), name='reading-material'), #10
    path('question/<int:question_id>/choices/', ChoicesView.as_view(), name='question-choice'),  #11
    path('<int:pk>/quiz/<slug:quiz_slug>/take/', QuizTake.as_view(), name="quiz_take"), #12      href="{% url 'quiz_take' pk=course.pk slug=quiz.slug %}
     path('course/<int:course_id>/quiz/<int:quiz_id>/question/', EditingQuestionInstanceOnConfirmationView.as_view(), name='editing-question-instance-on-confirmation'), 
    #superadmindashboardviews.py views url
    path('dashboard/sa/registration/count/', ActiveRegisteredCustomerCountView.as_view(), name='active-registration-count'),  #13
    path('dashboard/sa/active_registration-per-course/count/', CountOfActiveRegistrationPerCoure.as_view(), name='active_registration-per-course-count'),  #14
    path('dashboard/sa/progress-per-course/count/', GraphOfProgressPerCourseView.as_view(), name='not_started-per-course-count'),  #15
    path('dashboard/sa/course/count/', CourseCountView.as_view(), name='course-count'),  #16
    
    path('course-completion-status/', CourseCompletionStatusView.as_view(), name='course_completion_status'),
    path('quiz-score/', QuizScoreView.as_view(), name='quiz_score'),
    path('quiz-score-per-course/',QuizScorePerCourseView.as_view(), name='quiz_score_per_course'),
    path('course-completion-status-per-user/', CourseCompletionStatusPerUserView.as_view(), name='course_completion_status_per_user'),
    path('display-client-course-progress/', DisplayClientCourseProgressView.as_view(), name='display_client_course_progress'),
    path('count-courses-status/', CountCoursesStatusView.as_view(), name='count_client_completed_courses'),

    path('count-registered-courses/', RegisteredCourseCountView.as_view(), name='count_registered_courses'),
    path('active-enrolled-user-count/', ActiveEnrolledUserCountPerCustomerView.as_view(), name='active_enrolled_user_count'),
    path('progress-count/', ProgressCountView.as_view(), name='progress_count'),
    
    path('course/<int:course_id>/video-material/', UploadVideoToS3APIView.as_view(), name='reading-material'),
    
    path('course/<int:course_id>/notifications/', NotificationBasedOnCourseDisplayView.as_view(), name='course-notifications'),
    path('course/<int:course_id>/quiz/<int:quiz_id>/edit/', EditQuizInstanceOnConfirmationView.as_view(), name='edit_quiz_instance_confirmation'),
    #enrollcourseviews.py views url
    path('display/registered-course/', DisplayCourseListView.as_view(), name='course-list'), 
    path('display/users/', UserListForEnrollmentView.as_view(), name='users-list'), 
    path('course-enrollments/', CourseEnrollmentView.as_view(), name='course-enrollments-record'), 
    path('manage-enrollment/', ManageCourseEnrollmentView.as_view(), name='manage_enrollment'),
]
