from rest_framework import serializers

class ActiveCourseCountSerializer(serializers.Serializer):
    
    active_course_count = serializers.IntegerField()
    
    def validate_active_course_count(self, value):
        """
        Validate the active_course_count field.
        """
        if value < 0:
            raise serializers.ValidationError("Active course count cannot be negative.")
        return value


class InActiveCourseCountSerializer(serializers.Serializer):
    """
    Serializer for the inactive course count.
    """
    inactive_course_count = serializers.IntegerField()

    def validate_inactive_course_count(self, value):
        """
        Validate the inactive_course_count field.
        """
        if value < 0:
            raise serializers.ValidationError("Inactive course count cannot be negative.")
        return value


class ActiveRegistrationCountSerializer(serializers.Serializer):
    """
    Serializer for the active registration count.
    """
    active_registered_customer_count = serializers.IntegerField()
    
    def validate_active_registered_customer_count(self, value):
        """
        Validate the active_registered_customer_count field.
        """
        if value < 0:
            raise serializers.ValidationError("Active Registration count cannot be negative.")
        return value