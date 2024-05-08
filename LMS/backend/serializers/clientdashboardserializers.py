from rest_framework import serializers
from backend.models.allmodels import CourseEnrollment

class CourseEnrollmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField()
    course_id = serializers.IntegerField()

    class Meta:
        model = CourseEnrollment
        fields = ['id', 'user_id', 'course_id', 'active']

    def validate(self, data):
        # Add custom validation logic here
        # For example, you can check if 'active' is a boolean value
        active = data.get('active')
        if active is not None and not isinstance(active, bool):
            raise serializers.ValidationError("Active must be a boolean value")
        return data

class CountCoursesStatusSerializer(serializers.Serializer):
    active_enrollments_count = serializers.IntegerField()
    completed_courses_count = serializers.IntegerField()
    in_progress_courses_count = serializers.IntegerField()
    not_started_courses_count = serializers.IntegerField()

    def validate(self, data):
        # Validate each count to be positive
        for field_name, value in data.items():
            if value < 0:
                raise serializers.ValidationError(f"{field_name} count must be positive")
        return data