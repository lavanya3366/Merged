from rest_framework import serializers
from backend.models.allmodels import (Course, Notification, Question, UploadReadingMaterial, Quiz)

class EditCourseInstanceSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=True)
    summary = serializers.CharField(required=True)

    def validate(self, data):
        if not data['title'] or not data['summary']:
            raise serializers.ValidationError("Title and summary cannot be empty")
        return data
    
class NotificationSerializer(serializers.ModelSerializer):
    
    created_at = serializers.SerializerMethodField()
    
    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")
    
    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id', 'course', 'message', 'created_at']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data
    
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at']

class EditCourseInstanceSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=True)
    summary = serializers.CharField(required=True)

    def validate(self, data):
        if not data['title'] or not data['summary']:
            raise serializers.ValidationError("Title and summary cannot be empty")
        return data
    
class DeleteSelectedCourseSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()

    def validate_course_id(self, value):
        try:
            course = Course.objects.get(id=value)
            if course.active:
                raise serializers.ValidationError("Course must be inactive before deletion.")
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course not found.")
        return value

class UploadReadingMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadReadingMaterial
        fields = ['title', 'reading_content']

    def validate(self, data):
        """
        Validate the input data.
        """
        # Check if at least one of title or reading_content is provided
        if 'title' not in data and 'reading_content' not in data:
            raise serializers.ValidationError("At least one of title or reading_content is required.")
        return data

class DeleteReadingMaterialSerializer(serializers.Serializer):
    reading_material_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "Reading material ID is required.",
            "min_value": "Reading material ID must be a positive integer."
        }
    )

    def validate_reading_material_id(self, value):
        if not UploadReadingMaterial.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Reading material with the provided ID does not exist.")
        return value

class EditQuizInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'answers_at_end', 'exam_paper', 'pass_mark']

    def validate(self, data):
        # Check if title is provided
        if 'title' in data and not data['title']:
            raise serializers.ValidationError("Title cannot be empty.")

        # Check if description is provided
        if 'description' in data and not data['description']:
            raise serializers.ValidationError("Description cannot be empty.")

        # Check if pass_mark is a valid percentage
        if 'pass_mark' in data:
            pass_mark = data['pass_mark']
            if pass_mark < 0 or pass_mark > 100:
                raise serializers.ValidationError("Pass mark should be between 0 and 100.")

        # Your custom validations here
        return data
    
class DeleteSelectedQuizSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "Quiz ID is required.",
            "min_value": "Quiz ID must be a positive integer."
        }
    )

    def validate_quiz_id(self, value):
        # Check if the quiz with the provided ID exists
        if not Quiz.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Quiz with the provided ID does not exist.")
        return value
    
class EditQuestionInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['figure', 'content', 'explanation', 'choice_order']

    def validate(self, data):
        # Check if content is provided when not null
        if 'content' in data and not data['content']:
            raise serializers.ValidationError("Content cannot be empty when provided.")

        return data

class DeleteQuestionSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "Question ID is required.",
            "min_value": "Question ID must be a positive integer."
        }
    )

    def validate_question_id(self, value):
        # Check if the question with the provided ID exists
        if not Question.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Question with the provided ID does not exist.")
        return value

class EditQuizInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'answers_at_end', 'exam_paper', 'pass_mark']

    def validate(self, data):
        # Check if title is provided
        if 'title' in data and not data['title']:
            raise serializers.ValidationError("Title cannot be empty.")

        # Check if description is provided
        if 'description' in data and not data['description']:
            raise serializers.ValidationError("Description cannot be empty.")

        # Check if pass_mark is a valid percentage
        if 'pass_mark' in data:
            pass_mark = data['pass_mark']
            if pass_mark < 0 or pass_mark > 100:
                raise serializers.ValidationError("Pass mark should be between 0 and 100.")
        return data
    
class DeleteSelectedQuizSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "Quiz ID is required.",
            "min_value": "Quiz ID must be a positive integer."
        }
    )

    def validate_quiz_id(self, value):
        # Check if the quiz with the provided ID exists
        if not Quiz.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Quiz with the provided ID does not exist.")
        return value
    
class EditQuestionInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['figure', 'content', 'explanation', 'choice_order']

    def validate(self, data):
        # Check if content is provided when not null
        if 'content' in data and not data['content']:
            raise serializers.ValidationError("Content cannot be empty when provided.")

        return data

class DeleteQuestionSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "Question ID is required.",
            "min_value": "Question ID must be a positive integer."
        }
    )

    def validate_question_id(self, value):
        # Check if the question with the provided ID exists
        if not Question.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Question with the provided ID does not exist.")
        return value
    
class NotificationSerializer(serializers.ModelSerializer):
    
    created_at = serializers.SerializerMethodField()
    
    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")
    
    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id', 'course', 'message', 'created_at']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data
    
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at']