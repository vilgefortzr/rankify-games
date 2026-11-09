from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator
from django.core.exceptions import ValidationError as PasswordError

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, validators=[
        UniqueValidator(
            queryset=User.objects.all(), message="User with this email already exists."
        )], max_length=128)
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    password_confirmation = serializers.CharField(write_only=True, min_length=8, max_length=128)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "password_confirmation"
        ]

    def _check_password_strength(self, password, user):
        try:
            validate_password(password, user=user)
        except PasswordError as e:
            raise ValidationError({"password": e.messages})

    def validate(self, attrs):
        password = attrs['password']
        if password != attrs['password_confirmation']:
            raise ValidationError({"password_confirmation": ["Passwords don't match."]})
        attrs.pop('password_confirmation')
        user = User(**attrs)
        self._check_password_strength(password, user)
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

