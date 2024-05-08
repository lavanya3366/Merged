from datetime import timezone
from rest_framework import serializers
from backend.models.allmodels import Course, CourseEnrollment
from backend.models.coremodels import User

class RegisteredCourseSerializer(serializers.ModelSerializer):
    
    updated_at = serializers.SerializerMethodField()

    def get_updated_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id', 'title', 'updated_at','version_number']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data 
    class Meta:
        model = Course
        fields = ['id', 'title', 'updated_at','version_number']
        
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name']

    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id', 'first_name', 'last_name']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data 


class CourseEnrollmentSerializer(serializers.Serializer):
    course_ids = serializers.ListField(child=serializers.IntegerField())
    user_ids = serializers.ListField(child=serializers.IntegerField())

    def validate(self, data):
        course_ids = data.get("course_ids")
        user_ids = data.get("user_ids")

        if not course_ids:
            raise serializers.ValidationError("Course IDs are missing.")
        if not user_ids:
            raise serializers.ValidationError("User IDs are missing.")

        # You can add more custom validations here if needed

        return data  
         
class DisplayCourseEnrollmentSerializer(serializers.ModelSerializer):
    user_first_name = serializers.SerializerMethodField()
    user_last_name = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()  # Add this field

    class Meta:
        model = CourseEnrollment
        fields = ['user', 'user_first_name', 'user_last_name', 'course_title', 'active']  # Replace 'course' with 'course_title'

    def get_user_first_name(self, obj):
        return obj.user.first_name
    
    def get_user_last_name(self, obj):
        return obj.user.last_name

    def get_course_title(self, obj):  # Define method to get course title
        return obj.course.title  # Fetch the title of the course from the related object

    def validate(self, attrs):
        """
        Custom validation to ensure that the user and course fields exist.
        """
        user_id = attrs.get('user')
        course_id = attrs.get('course')
        
        # Check if the user exists
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")

        # Check if the course exists
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course does not exist.")

        return attrs

    def create(self, validated_data):
        return CourseEnrollment.objects.create(**validated_data)
    
class EnrolledCoursesSerializer(serializers.ModelSerializer):
    """Serializer for displaying enrolled courses."""
    
    class Meta:
        model = CourseEnrollment
        fields = ['id', 'course', 'enrolled_at', 'updated_at']
        
    def validate(self, data):
        required_fields=['id', 'course', 'enrolled_at', 'updated_at']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data

class EnrollmentDeleteSerializer(serializers.Serializer):
    """
    Serializer for deleting a course enrollment.
    """
    enrollment_id = serializers.IntegerField()

    def validate(self, data):
        # Validate enrollment_id
        if 'enrollment_id' not in data:
            raise serializers.ValidationError("Enrollment ID is required.")
        return data


class ManageCourseEnrollmentSerializer(serializers.Serializer):
    enrollment_ids = serializers.ListField(
        child=serializers.IntegerField(),  # Validates that each item in the list is an integer
        min_length=1,  # Ensures the list is not empty
        error_messages={
            'min_length': 'At least one enrollment ID must be provided.',  # Custom error message for empty list
        }
    )

    def validate_enrollment_ids(self, value):
        """
        Additional validation to check if enrollment IDs are valid and exist in the database.
        """
        # Check if all provided enrollment IDs exist in the database
        invalid_ids = []
        for enrollment_id in value:
            if not CourseEnrollment.objects.filter(id=enrollment_id).exists():
                invalid_ids.append(enrollment_id)

        if invalid_ids:
            raise serializers.ValidationError(f"The following enrollment IDs do not exist: {', '.join(map(str, invalid_ids))}")

        return value

    def validate(self, data):
        """
        Additional validation to ensure uniqueness of enrollment IDs.
        """
        enrollment_ids = data.get('enrollment_ids', [])

        # Check for duplicate enrollment IDs
        if len(enrollment_ids) != len(set(enrollment_ids)):
            raise serializers.ValidationError("Duplicate enrollment IDs are not allowed.")

        return data