from .models import Submission, QuizSubmission
from utils.api import serializers
from utils.serializers import LanguageNameChoiceField


class CreateSubmissionSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    language = LanguageNameChoiceField()
    code = serializers.CharField(max_length=1024 * 1024)
    contest_id = serializers.IntegerField(required=False)
    captcha = serializers.CharField(required=False)


class ShareSubmissionSerializer(serializers.Serializer):
    id = serializers.CharField()
    shared = serializers.BooleanField()


class SubmissionModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Submission
        fields = "__all__"


# 不显示submission info的serializer, 用于ACM rule_type
class SubmissionSafeModelSerializer(serializers.ModelSerializer):
    problem = serializers.SlugRelatedField(read_only=True, slug_field="_id")

    class Meta:
        model = Submission
        exclude = ("info", "contest", "ip")


class SubmissionListSerializer(serializers.ModelSerializer):
    problem = serializers.SlugRelatedField(read_only=True, slug_field="_id")
    show_link = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Submission
        exclude = ("info", "contest", "code", "ip")

    def get_show_link(self, obj):
        # 没传user或为匿名user
        if self.user is None or not self.user.is_authenticated:
            return False
        return obj.check_user_permission(self.user)

# quiz
class CreateQuizSubmissionSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField()
    submit = serializers.CharField(max_length=1024)
    contest_id = serializers.IntegerField(required=False)
    captcha = serializers.CharField(required=False)

class ShareSubmissionQuizSerializer(serializers.Serializer):
    id = serializers.CharField()
    shared = serializers.BooleanField()


class SubmissionQuizModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = QuizSubmission
        fields = "__all__"

# 不显示submission info的serializer, 用于ACM rule_type
class SubmissionQuizSafeModelSerializer(serializers.ModelSerializer):
    quiz = serializers.SlugRelatedField(read_only=True, slug_field="_id")

    class Meta:
        model = QuizSubmission
        exclude = ("info", "contest", "ip")


class SubmissionQuizListSerializer(serializers.ModelSerializer):
    quiz = serializers.SlugRelatedField(read_only=True, slug_field="_id")
    show_link = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = QuizSubmission
        exclude = ("info", "contest", "submit", "ip")

    def get_show_link(self, obj):
        # 没传user或为匿名user
        if self.user is None or not self.user.is_authenticated:
            return False
        return obj.check_user_permission(self.user)
