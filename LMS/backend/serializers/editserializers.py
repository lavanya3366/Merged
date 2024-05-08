from rest_framework import serializers
from backend.models.allmodels import Choice, Course, CourseStructure, Notification, Question, UploadReadingMaterial, UploadVideo, Quiz
   
        
class EditingQuizInstanceOnConfirmationSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, max_length=60)
    description = serializers.CharField(required=False)
    answers_at_end = serializers.BooleanField(required=False)
    exam_paper = serializers.BooleanField(required=False)
    pass_mark = serializers.IntegerField(required=False, min_value=0, max_value=100)
    confirmation = serializers.BooleanField()

    def validate(self, data):
        confirmation = data.get('confirmation')
        if confirmation is None:
            raise serializers.ValidationError("Confirmation field is required.")

        if confirmation and not any(data.values()):
            raise serializers.ValidationError("At least one field to update is required.")

        return data
    
class EditingQuestionInstanceOnConfirmationSerializer(serializers.Serializer):
    confirmation = serializers.BooleanField()

    figure = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    explanation = serializers.CharField(required=False, allow_blank=True)
    choice_order = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """
        Validate the input data.
        """
        confirmation = data.get('confirmation')
        
        # Check if confirmation is provided and is a boolean value
        if confirmation is None:
            raise serializers.ValidationError("Confirmation is required.")
        
        # Additional validations can be added here
        
        return data