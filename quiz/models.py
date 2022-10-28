from unittest.util import _MAX_LENGTH
from django.db import models
from utils.models import JSONField

from account.models import User
from contest.models import Contest
from utils.models import RichTextField
from utils.constants import Choices


class QuizTag(models.Model):
    name = models.TextField()

    class Meta:
        db_table = "quiz_tag"


class QuizRuleType(Choices):
    ACM = "ACM"
    OI = "OI"

class QuizQuizType(Choices):
    Short = "Short"
    Multiple = "Multiple"
class QuizDifficulty(object):
    High = "High"
    Mid = "Mid"
    Low = "Low"


class QuizIOMode(Choices):
    standard = "Standard IO"
    file = "File IO"


def _default_io_mode():
    return {"io_mode": QuizIOMode.standard, "input": "input.txt", "output": "output.txt"}


class Quiz(models.Model):
    # display ID
    _id = models.TextField(db_index=True)
    contest = models.ForeignKey(Contest, null=True, on_delete=models.CASCADE)
    # for contest quiz
    is_public = models.BooleanField(default=False)
    title = models.TextField()
    # HTML
    description = RichTextField()
    # [{input: "test", output: "123"}, {input: "test123", output: "456"}]
    # [{"input_name": "1.in", "output_name": "1.out", "score": 0}]
    create_time = models.DateTimeField(auto_now_add=True)
    # we can not use auto_now here
    last_update_time = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    # ms
    
    # special judge related
    rule_type = models.TextField()
    quiz_type = models.TextField()
    visible = models.BooleanField(default=True)
    difficulty = models.TextField()
    tags = models.ManyToManyField(QuizTag)
    # for OI mode
    total_score = models.IntegerField(default=0)
    submission_number = models.BigIntegerField(default=0)
    accepted_number = models.BigIntegerField(default=0)
    # {JudgeStatus.ACCEPTED: 3, JudgeStaus.WRONG_ANSWER: 11}, the number means count
    statistic_info = JSONField(default=dict)
    share_submission = models.BooleanField(default=False)
    
    op1 = models.CharField(max_length=200,null=True)
    op2 = models.CharField(max_length=200,null=True)
    op3 = models.CharField(max_length=200,null=True)
    op4 = models.CharField(max_length=200,null=True)
    op5 = models.CharField(max_length=200,null=True)
    ans = models.CharField(max_length=200,null=True)
    
    class Meta:
        db_table = "quiz"
        unique_together = (("_id", "contest"),)
        ordering = ("create_time",)

    def add_submission_number(self):
        self.submission_number = models.F("submission_number") + 1
        self.save(update_fields=["submission_number"])

    def add_ac_number(self):
        self.accepted_number = models.F("accepted_number") + 1
        self.save(update_fields=["accepted_number"])
