from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["display_name", "avatar_url", "created_at"]
        read_only_fields = ["created_at"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "profile"]


class RegisterSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password", "display_name"]

    def create(self, validated_data):
        display_name = validated_data.pop("display_name", "")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        user.profile.display_name = display_name
        user.profile.save()
        return user

    def to_representation(self, instance):
        refresh = RefreshToken.for_user(instance)
        return {
            "id": instance.pk,
            "username": instance.username,
            "email": instance.email,
            "profile": UserProfileSerializer(instance.profile).data,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }


class ProfileUpdateSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(
        max_length=100, required=False, allow_blank=True, source="profile.display_name"
    )
    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = ["email", "display_name"]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        instance.email = validated_data.get("email", instance.email)
        instance.save()
        if profile_data:
            instance.profile.display_name = profile_data.get(
                "display_name", instance.profile.display_name
            )
            instance.profile.save()
        return instance

    def to_representation(self, instance):
        return {
            "id": instance.pk,
            "username": instance.username,
            "email": instance.email,
            "profile": {
                "display_name": instance.profile.display_name,
                "avatar_url": instance.profile.avatar_url,
                "created_at": instance.profile.created_at,
            },
        }
