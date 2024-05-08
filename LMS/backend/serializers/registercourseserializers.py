from rest_framework import serializers
from backend.models.allmodels import Course, CourseRegisterRecord
from backend.models.coremodels import Customer


class FirstVersionActiveCourseListSerializer(serializers.ModelSerializer):
    """
    Serializer for Course model for First Version Course.
    """
    updated_at = serializers.SerializerMethodField()

    def get_updated_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")
    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id','title','updated_at','version_number']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data
    class Meta:
        model = Course
        fields = ['id', 'title', 'updated_at', 'version_number']


class DerivedVersionActiveCourseListSerializer(serializers.ModelSerializer):
    """
    Serializer for Course model for non-first version courses.
    """
    original_course = serializers.CharField(source='original_course.title', read_only=True, allow_null=True)
    updated_at = serializers.SerializerMethodField()

    def get_updated_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")
    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id','title','updated_at','original_course', 'version_number']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data
    class Meta:
        model = Course
        fields = ['id','title','updated_at','original_course', 'version_number']


class CourseRegisterRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for creating records in CourseRegisterRecord model.
    """
    
    def validate(self, data):
        # Validate course ID
        course = data.get('course')
        if not Course.objects.filter(pk=course.id).exists():
            raise serializers.ValidationError(f"Course with ID {course} does not exist.")
        # Validate customer ID
        customer = data.get('customer')
        if not Customer.objects.filter(pk=customer.id).exists():
            raise serializers.ValidationError(f"Customer with ID {customer} does not exist.")
        return data
    class Meta:
        model = CourseRegisterRecord
        fields = '__all__'


class DisplayCourseRegisterRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying records in CourseRegisterRecord model.
    """
    customer = serializers.CharField(source='customer.name', read_only=True)
    course = serializers.CharField(source='course.title', read_only=True)
    created_at = serializers.SerializerMethodField()  # Custom method to format created_at

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")  # Format the created_at field as date only

    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id', 'customer', 'course', 'created_at', 'active']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data
    class Meta:
        model = CourseRegisterRecord
        fields = ['id', 'customer', 'course', 'created_at', 'active']


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for the Customer model.
    """
    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id','name']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data
    class Meta:
        model = Customer
        fields = ['id', 'name']

