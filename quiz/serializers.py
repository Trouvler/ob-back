import re

from django import forms

from options.options import SysOptions
from utils.api import UsernameSerializer, serializers
from utils.constants import Difficulty
from utils.serializers import LanguageNameMultiChoiceField, SPJLanguageNameChoiceField, LanguageNameChoiceField

from .models import Quiz, QuizRuleType, QuizTag, QuizIOMode, QuizQuizType



class CreateSampleSerializer(serializers.Serializer):
    input = serializers.CharField(trim_whitespace=False)
    output = serializers.CharField(trim_whitespace=False)




class QuizIOModeSerializer(serializers.Serializer):
    io_mode = serializers.ChoiceField(choices=QuizIOMode.choices())
    input = serializers.CharField()
    output = serializers.CharField()

    def validate(self, attrs):
        if attrs["input"] == attrs["output"]:
            raise serializers.ValidationError("Invalid io mode")
        for item in (attrs["input"], attrs["output"]):
            if not re.match("^[a-zA-Z0-9.]+$", item):
                raise serializers.ValidationError("Invalid io file name format")
        return attrs


class CreateOrEditQuizSerializer(serializers.Serializer):
    _id = serializers.CharField(max_length=32, allow_blank=True, allow_null=True)
    title = serializers.CharField(max_length=1024)
    description = serializers.CharField()
    rule_type = serializers.ChoiceField(choices=[QuizRuleType.ACM, QuizRuleType.OI])
    quiz_type = serializers.ChoiceField(choices=[QuizQuizType.Short, QuizQuizType.Multiple])
    ans = serializers.CharField(max_length=200)
    op1 = serializers.CharField(max_length=200)
    op2 = serializers.CharField(max_length=200)
    op3 = serializers.CharField(max_length=200)
    op4 = serializers.CharField(max_length=200)
    op5 = serializers.CharField(max_length=200)
    visible = serializers.BooleanField()
    difficulty = serializers.ChoiceField(choices=Difficulty.choices())
    tags = serializers.ListField(child=serializers.CharField(max_length=32), allow_empty=False)
    share_submission = serializers.BooleanField()


class CreateQuizSerializer(CreateOrEditQuizSerializer):
    pass


class EditQuizSerializer(CreateOrEditQuizSerializer):
    id = serializers.IntegerField()


class CreateContestQuizSerializer(CreateOrEditQuizSerializer):
    contest_id = serializers.IntegerField()


class EditContestQuizSerializer(CreateOrEditQuizSerializer):
    id = serializers.IntegerField()
    contest_id = serializers.IntegerField()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizTag
        fields = "__all__"


class BaseQuizSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)
    created_by = UsernameSerializer()


class QuizAdminSerializer(BaseQuizSerializer):
    class Meta:
        model = Quiz
        fields = "__all__"


class QuizSerializer(BaseQuizSerializer):

    class Meta:
        model = Quiz
        exclude = ("visible", "is_public")


class QuizSafeSerializer(BaseQuizSerializer):

    class Meta:
        model = Quiz
        exclude = ("visible", "is_public",
                   "difficulty", "submission_number", "accepted_number", "statistic_info")


class ContestQuizMakePublicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_id = serializers.CharField(max_length=32)


class ExportQuizSerializer(serializers.ModelSerializer):
    display_id = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)

    def get_display_id(self, obj):
        return obj._id

    def _html_format_value(self, value):
        return {"format": "html", "value": value}

    def get_description(self, obj):
        return self._html_format_value(obj.description)

    class Meta:
        model = Quiz
        fields = ("display_id", "title", "description", "tags",
                "rule_type", "quiz_type")


class AddContestQuizSerializer(serializers.Serializer):
    contest_id = serializers.IntegerField()
    quiz_id = serializers.IntegerField()
    display_id = serializers.CharField()


class ExportQuizRequestSerialzier(serializers.Serializer):
    quiz_id = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class UploadQuizForm(forms.Form):
    file = forms.FileField()


class FormatValueSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=["html", "markdown"])
    value = serializers.CharField(allow_blank=True)

class AnswerSerializer(serializers.Serializer):
    code = serializers.CharField()
    language = LanguageNameChoiceField()


class ImportQuizSerializer(serializers.Serializer):
    display_id = serializers.CharField(max_length=128)
    title = serializers.CharField(max_length=128)
    description = FormatValueSerializer()
    rule_type = serializers.ChoiceField(choices=QuizRuleType.choices())
    quiz_type = serializers.ChoiceField(choices=QuizQuizType.choices())
    answers = serializers.ListField(child=AnswerSerializer())
    tags = serializers.ListField(child=serializers.CharField())


class FPSQuizSerializer(serializers.Serializer):
    class UnitSerializer(serializers.Serializer):
        unit = serializers.ChoiceField(choices=["MB", "s", "ms"])
        value = serializers.IntegerField(min_value=1, max_value=60000)

    title = serializers.CharField(max_length=128)
    description = serializers.CharField()
    append = serializers.ListField(child=serializers.DictField(), allow_empty=True, allow_null=True)
    prepend = serializers.ListField(child=serializers.DictField(), allow_empty=True, allow_null=True)
