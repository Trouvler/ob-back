import hashlib
import json
import os
# import shutil
import tempfile
import zipfile
from wsgiref.util import FileWrapper

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import StreamingHttpResponse, FileResponse

from account.decorators import quiz_permission_required, ensure_created_by
from contest.models import Contest, ContestStatus
from fps.parser import FPSHelper, FPSParser
from options.options import SysOptions
from submission.models import Submission, JudgeStatus_quiz
from utils.api import APIView, CSRFExemptAPIView_quiz, validate_serializer, APIError
from utils.constants import Difficulty
from utils.shortcuts import rand_str, natural_sort_key
from utils.tasks import delete_files
from ..models import Quiz, QuizRuleType, QuizTag
from ..serializers import (CreateContestQuizSerializer,
                           CreateQuizSerializer, EditQuizSerializer, EditContestQuizSerializer,
                           QuizAdminSerializer, ContestQuizMakePublicSerializer,
                           AddContestQuizSerializer)
from ..utils import TEMPLATE_BASE, build_quiz_template


class QuizBase(APIView):
    def common_checks(self, request):
        data = request.data
        if data["rule_type"] == QuizRuleType.OI:
            total_score = 0
            for item in data["test_case_score"]:
                if item["score"] <= 0:
                    return "Invalid score"
                else:
                    total_score += item["score"]
            data["total_score"] = total_score


class QuizAPI(QuizBase):
    @quiz_permission_required
    @validate_serializer(CreateQuizSerializer)
    def post(self, request):
        data = request.data
        _id = data["_id"]
        if not _id:
            return self.error("Display ID is required")
        if Quiz.objects.filter(_id=_id, contest_id__isnull=True).exists():
            return self.error("Display ID already exists")

        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)

        # todo check filename and score info
        tags = data.pop("tags")
        data["created_by"] = request.user
        quiz = Quiz.objects.create(**data)

        for item in tags:
            try:
                tag = QuizTag.objects.get(name=item)
            except QuizTag.DoesNotExist:
                tag = QuizTag.objects.create(name=item)
            quiz.tags.add(tag)
        return self.success(QuizAdminSerializer(quiz).data)

    @quiz_permission_required
    def get(self, request):
        quiz_id = request.GET.get("id")
        rule_type = request.GET.get("rule_type")
        user = request.user
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                ensure_created_by(quiz, request.user)
                return self.success(QuizAdminSerializer(quiz).data)
            except Quiz.DoesNotExist:
                return self.error("Quiz does not exist")

        quizs = Quiz.objects.filter(contest_id__isnull=True).order_by("-create_time")
        if rule_type:
            if rule_type not in QuizRuleType.choices():
                return self.error("Invalid rule_type")
            else:
                quizs = quizs.filter(rule_type=rule_type)

        keyword = request.GET.get("keyword", "").strip()
        if keyword:
            quizs = quizs.filter(Q(title__icontains=keyword) | Q(_id__icontains=keyword))
        if not user.can_mgmt_all_quiz():
            quizs = quizs.filter(created_by=user)
        return self.success(self.paginate_data(request, quizs, QuizAdminSerializer))

    @quiz_permission_required
    @validate_serializer(EditQuizSerializer)
    def put(self, request):
        data = request.data
        quiz_id = data.pop("id")

        try:
            quiz = Quiz.objects.get(id=quiz_id)
            ensure_created_by(quiz, request.user)
        except Quiz.DoesNotExist:
            return self.error("Quiz does not exist")

        _id = data["_id"]
        if not _id:
            return self.error("Display ID is required")
        if Quiz.objects.exclude(id=quiz_id).filter(_id=_id, contest_id__isnull=True).exists():
            return self.error("Display ID already exists")

        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)
        # todo check filename and score info
        tags = data.pop("tags")

        for k, v in data.items():
            setattr(quiz, k, v)
        quiz.save()

        quiz.tags.remove(*quiz.tags.all())
        for tag in tags:
            try:
                tag = QuizTag.objects.get(name=tag)
            except QuizTag.DoesNotExist:
                tag = QuizTag.objects.create(name=tag)
            quiz.tags.add(tag)

        return self.success()

    @quiz_permission_required
    def delete(self, request):
        id = request.GET.get("id")
        if not id:
            return self.error("Invalid parameter, id is required")
        try:
            quiz = Quiz.objects.get(id=id, contest_id__isnull=True)
        except Quiz.DoesNotExist:
            return self.error("Quiz does not exists")
        ensure_created_by(quiz, request.user)
        # d = os.path.join(settings.TEST_CASE_DIR, quiz.test_case_id)
        # if os.path.isdir(d):
        #     shutil.rmtree(d, ignore_errors=True)
        quiz.delete()
        return self.success()


class ContestQuizAPI(QuizBase):
    @validate_serializer(CreateContestQuizSerializer)
    def post(self, request):
        data = request.data
        try:
            contest = Contest.objects.get(id=data.pop("contest_id"))
            ensure_created_by(contest, request.user)
        except Contest.DoesNotExist:
            return self.error("Contest does not exist")

        if data["rule_type"] != contest.rule_type:
            return self.error("Invalid rule type")

        _id = data["_id"]
        if not _id:
            return self.error("Display ID is required")

        if Quiz.objects.filter(_id=_id, contest=contest).exists():
            return self.error("Duplicate Display id")

        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)

        # todo check filename and score info
        data["contest"] = contest
        tags = data.pop("tags")
        data["created_by"] = request.user
        quiz = Quiz.objects.create(**data)

        for item in tags:
            try:
                tag = QuizTag.objects.get(name=item)
            except QuizTag.DoesNotExist:
                tag = QuizTag.objects.create(name=item)
            quiz.tags.add(tag)
        return self.success(QuizAdminSerializer(quiz).data)

    def get(self, request):
        quiz_id = request.GET.get("id")
        contest_id = request.GET.get("contest_id")
        user = request.user
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                ensure_created_by(quiz.contest, user)
            except Quiz.DoesNotExist:
                return self.error("Quiz does not exist")
            return self.success(QuizAdminSerializer(quiz).data)

        if not contest_id:
            return self.error("Contest id is required")
        try:
            contest = Contest.objects.get(id=contest_id)
            ensure_created_by(contest, user)
        except Contest.DoesNotExist:
            return self.error("Contest does not exist")
        quizs = Quiz.objects.filter(contest=contest).order_by("-create_time")
        if user.is_admin():
            quizs = quizs.filter(contest__created_by=user)
        keyword = request.GET.get("keyword")
        if keyword:
            quizs = quizs.filter(title__contains=keyword)
        return self.success(self.paginate_data(request, quizs, QuizAdminSerializer))

    @validate_serializer(EditContestQuizSerializer)
    def put(self, request):
        data = request.data
        user = request.user

        try:
            contest = Contest.objects.get(id=data.pop("contest_id"))
            ensure_created_by(contest, user)
        except Contest.DoesNotExist:
            return self.error("Contest does not exist")

        if data["rule_type"] != contest.rule_type:
            return self.error("Invalid rule type")

        quiz_id = data.pop("id")

        try:
            quiz = Quiz.objects.get(id=quiz_id, contest=contest)
        except Quiz.DoesNotExist:
            return self.error("Quiz does not exist")

        _id = data["_id"]
        if not _id:
            return self.error("Display ID is required")
        if Quiz.objects.exclude(id=quiz_id).filter(_id=_id, contest=contest).exists():
            return self.error("Display ID already exists")

        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)
        # todo check filename and score info
        tags = data.pop("tags")
        for k, v in data.items():
            setattr(quiz, k, v)
        quiz.save()

        quiz.tags.remove(*quiz.tags.all())
        for tag in tags:
            try:
                tag = QuizTag.objects.get(name=tag)
            except QuizTag.DoesNotExist:
                tag = QuizTag.objects.create(name=tag)
            quiz.tags.add(tag)
        return self.success()

    def delete(self, request):
        id = request.GET.get("id")
        if not id:
            return self.error("Invalid parameter, id is required")
        try:
            quiz = Quiz.objects.get(id=id, contest_id__isnull=False)
        except Quiz.DoesNotExist:
            return self.error("Quiz does not exists")
        ensure_created_by(quiz.contest, request.user)
        if Submission.objects.filter(quiz=quiz).exists():
            return self.error("Can't delete the quiz as it has submissions")
        # d = os.path.join(settings.TEST_CASE_DIR, quiz.test_case_id)
        # if os.path.isdir(d):
        #    shutil.rmtree(d, ignore_errors=True)
        quiz.delete()
        return self.success()


class MakeContestQuizPublicAPIView(APIView):
    @validate_serializer(ContestQuizMakePublicSerializer)
    @quiz_permission_required
    def post(self, request):
        data = request.data
        display_id = data.get("display_id")
        if Quiz.objects.filter(_id=display_id, contest_id__isnull=True).exists():
            return self.error("Duplicate display ID")

        try:
            quiz = Quiz.objects.get(id=data["id"])
        except Quiz.DoesNotExist:
            return self.error("Quiz does not exist")

        if not quiz.contest or quiz.is_public:
            return self.error("Already be a public quiz")
        quiz.is_public = True
        quiz.save()
        # https://docs.djangoproject.com/en/1.11/topics/db/queries/#copying-model-instances
        tags = quiz.tags.all()
        quiz.pk = None
        quiz.contest = None
        quiz._id = display_id
        quiz.visible = False
        quiz.submission_number = quiz.accepted_number = 0
        quiz.statistic_info = {}
        quiz.save()
        quiz.tags.set(tags)
        return self.success()


class AddContestQuizAPI(APIView):
    @validate_serializer(AddContestQuizSerializer)
    def post(self, request):
        data = request.data
        try:
            contest = Contest.objects.get(id=data["contest_id"])
            quiz = Quiz.objects.get(id=data["quiz_id"])
        except (Contest.DoesNotExist, Quiz.DoesNotExist):
            return self.error("Contest or Quiz does not exist")

        if contest.status == ContestStatus.CONTEST_ENDED:
            return self.error("Contest has ended")
        if Quiz.objects.filter(contest=contest, _id=data["display_id"]).exists():
            return self.error("Duplicate display id in this contest")

        tags = quiz.tags.all()
        quiz.pk = None
        quiz.contest = contest
        quiz.is_public = True
        quiz.visible = True
        quiz._id = request.data["display_id"]
        quiz.submission_number = quiz.accepted_number = 0
        quiz.statistic_info = {}
        quiz.save()
        quiz.tags.set(tags)
        return self.success()
