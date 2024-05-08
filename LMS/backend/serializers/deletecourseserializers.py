from rest_framework import serializers
from backend.models.allmodels import Choice, CourseStructure
from backend.models.allmodels import (
    Choice, 
    Course, 
    CourseStructure,
    Notification,
    Question, 
    UploadReadingMaterial,
    UploadVideo, 
    Quiz
)
class EditCourseInstanceSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=True)
    summary = serializers.CharField(required=True)

    def validate(self, data):
        if not data['title'] or not data['summary']:
            raise serializers.ValidationError("Title and summary cannot be empty")
        return data
class DeleteCourseStructureSerializer(serializers.Serializer):
    instance_id = serializers.IntegerField(        required=True,
        min_value=1,
        error_messages={
            "required": "Instance ID is required.",
            "min_value": "Instance ID must be a positive integer."
        })

    def validate_instance_id(self, value):
         # Check if the quiz with the provided ID exists
        if not CourseStructure.objects.filter(pk=value).exists():
            raise serializers.ValidationError("coursestructure with the provided ID does not exist.")
        return value
class DeleteChoiceSerializer(serializers.Serializer):
    choice_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "Choice ID is required.",
            "min_value": "Choice ID must be a positive integer."
        }
    )

    def validate_quiz_id(self, value):
        # Check if the quiz with the provided ID exists
        if not Choice.objects.filter(pk=value).exists():
            raise serializers.ValidationError("choice with the provided ID does not exist.")
        return value
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
    