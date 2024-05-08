from rest_framework import serializers
from backend.models.allmodels import UploadVideo
from django.core.validators import FileExtensionValidator

class UploadVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadVideo
        fields = ('id', 'title', 'video', 'summary')
        read_only_fields = ('id',)

    def validate_video(self, value):
        """
        Check if the uploaded file is a valid video file.
        """
        valid_extensions = ['mp4', 'mkv', 'wmv', '3gp', 'f4v', 'avi', 'mp3']
        extension = value.name.split('.')[-1].lower()
        if extension not in valid_extensions:
            raise serializers.ValidationError(f"Unsupported file format: {extension}. Valid formats are: {', '.join(valid_extensions)}")
        return value

    def validate(self, data):
        """
        Validate the title and video fields.
        """
        title = data.get('title')
        video = data.get('video')

        # Validate title
        if not title:
            raise serializers.ValidationError("Title is required.")

        # Validate video
        if not video:
            raise serializers.ValidationError("Video file is required.")

        return data


class DeleteVideoMaterialSerializer(serializers.Serializer):
    video_material_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "Video material ID is required.",
            "min_value": "Video material ID must be a positive integer."
        }
    )

    def validate_video_material_id(self, value):
        if not UploadVideo.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Video material with the provided ID does not exist.")
        return value

class VideoMaterialSerializer(serializers.ModelSerializer):

    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id', 'title', 'url']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data
    class Meta:
        model = UploadVideo
        fields = ['id', 'title', 'url', 'summary']
        
        
        
class VideoMaterialListPerCourseSerializer(serializers.ModelSerializer):

    uploaded_at = serializers.SerializerMethodField()
    
    def get_uploaded_at(self, obj):
        return obj.uploaded_at.strftime("%Y-%m-%d")
    
    def validate(self, data):
        # Field Existence and Null Field Handling
        required_fields = ['id', 'title', 'uploaded_at']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required")
        return data
    class Meta:
        model = UploadVideo
        fields = ['id', 'title', 'uploaded_at']
        


class VideoMaterialCountPerCourseSerializer(serializers.Serializer):
    """
    Serializer for the active registration count.
    """
    video_material_count = serializers.IntegerField()
    
    def validate_video_material_count(self, value):
        """
        Validate the video_material_count field.
        """
        if value < 0:
            raise serializers.ValidationError(" Video Material count cannot be negative.")
        return value