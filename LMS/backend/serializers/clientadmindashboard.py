from rest_framework import serializers
from backend.models.coremodels import Customer


class ActiveEnrolledUserCountSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=True)

    def validate_customer_id(self, value):
        """
        Ensure that customer_id is provided and is a positive integer.
        """
        if value is None:
            raise serializers.ValidationError("Customer ID is required")
        if value <= 0:
            raise serializers.ValidationError("Customer ID must be a positive integer")
        return value
    
class RegisteredCourseCountSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()

    def validate_customer_id(self, value):
        """
        Ensure that customer_id is provided and is a positive integer.
        """
        if value is None:
            raise serializers.ValidationError("Customer ID is required")
        if value <= 0:
            raise serializers.ValidationError("Customer ID must be a positive integer")
        if not Customer.objects.filter(id=value).exists():
            raise serializers.ValidationError("Customer does not exist")
        return value
    
    
class ProgressDataSerializer(serializers.Serializer):
    course_title = serializers.CharField()
    completion_count = serializers.IntegerField()
    in_progress_count = serializers.IntegerField()
    not_started_count = serializers.IntegerField()

    def validate(self, data):
        """
        Validate that all count fields are positive.
        """
        if not data.get('course_title'):
            raise serializers.ValidationError("course_title is required")
        if data.get('completion_count') < 0:
            raise serializers.ValidationError("Completion count must be a positive integer.")
        if data.get('in_progress_count') < 0:
            raise serializers.ValidationError("In progress count must be a positive integer.")
        if data.get('not_started_count') < 0:
            raise serializers.ValidationError("Not started count must be a positive integer.")

        return data