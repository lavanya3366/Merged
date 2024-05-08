from rest_framework import serializers
from backend.models.allmodels import CourseCompletionStatusPerUser
from backend.models.allmodels import QuizScore

class CourseCompletionStatusSerializer(serializers.ModelSerializer):
    enrolled_user_id = serializers.IntegerField()
    course_id = serializers.IntegerField()

    class Meta:
        model = CourseCompletionStatusPerUser
        fields = ['enrolled_user_id', 'course_id', 'status', 'created_at']

    def validate(self, data):
        # Add custom validation logic here
        enrolled_user_id = data.get('enrolled_user_id')
        course_id = data.get('course_id')
        status = data.get('status')
        
        if enrolled_user_id is None:
            raise serializers.ValidationError("Enrolled user ID is required")

        if course_id is None:
            raise serializers.ValidationError("Course ID is required")

        if status not in ['completed', 'in_progress', 'not_started']:
            raise serializers.ValidationError("Status must be 'completed', 'in_progress', or 'not_started'")
        
        return data



class QuizScoreSerializer(serializers.ModelSerializer):
    enrolled_user_id = serializers.IntegerField()
    course_id = serializers.IntegerField()

    class Meta:
        model = QuizScore
        fields = ['enrolled_user_id', 'course_id', 'total_quizzes_per_course', 'completed_quiz_count', 'total_score_per_course', 'created_at', 'updated_at', 'active']

    def validate(self, data):
        # Add custom validation logic here
        enrolled_user_id = data.get('enrolled_user_id')
        course_id = data.get('course_id')
        total_quizzes_per_course = data.get('total_quizzes_per_course')
        completed_quiz_count = data.get('completed_quiz_count')
        total_score_per_course = data.get('total_score_per_course')
        
        if enrolled_user_id is None:
            raise serializers.ValidationError("Enrolled user ID is required")

        if course_id is None:
            raise serializers.ValidationError("Course ID is required")

        if total_quizzes_per_course is not None and total_quizzes_per_course <= 0:
            raise serializers.ValidationError("Total quizzes must be a positive integer")

        if completed_quiz_count is not None and completed_quiz_count < 0:
            raise serializers.ValidationError("Completed quiz count must be a non-negative integer")

        if total_score_per_course is not None and total_score_per_course < 0:
            raise serializers.ValidationError("Total score per course must be a non-negative number")

        return data