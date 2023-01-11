import hashlib
import json
import logging
from urllib.parse import urljoin

import requests
from django.db import transaction, IntegrityError
from django.db.models import F

from account.models import User
from contest.models import ContestRuleType, ACMContestRank, OIContestRank, ContestStatus
from options.options import SysOptions
from quiz.models import Quiz, QuizRuleType
from quiz.utils import parse_quiz_template
from submission.models import JudgeStatus_quiz, QuizSubmission
from utils.api.api import APIView
from utils.cache import cache
from utils.constants import CacheKey

logger = logging.getLogger(__name__)

# 继续处理在队列中的问题
def process_pending_task():
    if cache.llen(CacheKey.waiting_queue):
        # 防止循环引入
        from judge.tasks import judge_task_quiz
        tmp_data = cache.rpop(CacheKey.waiting_queue)
        if tmp_data:
            data = json.loads(tmp_data.decode("utf-8"))
            judge_task_quiz.send(**data)



class JudgeDispatcher_quiz(APIView):
    
    def __init__(self, submission_id, quiz_id):
        super().__init__()
        self.submission = QuizSubmission.objects.get(id=submission_id)
        self.contest_id = self.submission.contest_id
        self.last_result = self.submission.result if self.submission.info else None

        if self.contest_id:
            self.quiz = Quiz.objects.select_related("contest").get(id=quiz_id, contest_id=self.contest_id)
            self.contest = self.quiz.contest
        else:
            self.quiz = Quiz.objects.get(id=quiz_id)

    print("judge_task_quiz1")
    def judge(self):

        self.submit = self.submission.submit
        self.ans = self.quiz.ans

        data = {
            "sub": self.submit,
            'ans': self.ans
        }
        print("judge_task_quiz2")
        if data["sub"] == data["ans"]:
            self.submission.result = JudgeStatus_quiz.CORRECT
        else:
            self.submission.result = JudgeStatus_quiz.WROW
        logger.info("abc"+ self.ans)
        self.submission.save()
        logging.info("Log message goes here.")
        if self.contest_id:
            if self.contest.status != ContestStatus.CONTEST_UNDERWAY or \
                    User.objects.get(id=self.submission.user_id).is_contest_admin(self.contest):
                logger.info(
                    "Contest debug mode, id: " + str(self.contest_id) + ", submission id: " + self.submission.id)
                return
            with transaction.atomic():
                self.update_contest_quiz_status()
                self.update_contest_rank()
        else:
            if self.last_result:
                self.update_quiz_status_rejudge()
            else:
                self.update_quiz_status()

        # 至此判题结束，尝试处理任务队列中剩余的任务
        process_pending_task()

    def update_quiz_status_rejudge(self):
        result = str(self.submission.result)
        quiz_id = str(self.quiz.id)
        with transaction.atomic():
            # update quiz status
            quiz = Quiz.objects.select_for_update().get(contest_id=self.contest_id, id=self.quiz.id)
            if self.last_result != JudgeStatus_quiz.CORRECT and self.submission.result == JudgeStatus_quiz.CORRECT:
                quiz.accepted_number += 1
            quiz_info = quiz.statistic_info
            quiz_info[self.last_result] = quiz_info.get(self.last_result, 1) - 1
            quiz_info[result] = quiz_info.get(result, 0) + 1
            quiz.save(update_fields=["accepted_number", "statistic_info"])

            profile = User.objects.select_for_update().get(id=self.submission.user_id).userprofile
            if quiz.rule_type == QuizRuleType.ACM:
                acm_quizs_status = profile.acm_quizs_status.get("quizs", {})
                if acm_quizs_status[quiz_id]["status"] != JudgeStatus_quiz.CORRECT:
                    acm_quizs_status[quiz_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus_quiz.CORRECT:
                        profile.accepted_number += 1
                profile.acm_quizs_status["quizs"] = acm_quizs_status
                profile.save(update_fields=["accepted_number", "acm_quizs_status"])

            else:
                oi_quizs_status = profile.oi_quizs_status.get("quizs", {})
                score = self.submission.statistic_info["score"]
                if oi_quizs_status[quiz_id]["status"] != JudgeStatus_quiz.CORRECT:
                    # minus last time score, add this tim score
                    profile.add_score(this_time_score=score,
                                      last_time_score=oi_quizs_status[quiz_id]["score"])
                    oi_quizs_status[quiz_id]["score"] = score
                    oi_quizs_status[quiz_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus_quiz.CORRECT:
                        profile.accepted_number += 1
                profile.oi_quizs_status["quizs"] = oi_quizs_status
                profile.save(update_fields=["accepted_number", "oi_quizs_status"])

    def update_quiz_status(self):
        result = str(self.submission.result)
        quiz_id = str(self.quiz.id)
        with transaction.atomic():
            # update quiz status
            quiz = Quiz.objects.select_for_update().get(contest_id=self.contest_id, id=self.quiz.id)
            quiz.submission_number += 1
            if self.submission.result == JudgeStatus_quiz.CORRECT:
                quiz.accepted_number += 1
            quiz_info = quiz.statistic_info
            quiz_info[result] = quiz_info.get(result, 0) + 1
            quiz.save(update_fields=["accepted_number", "submission_number", "statistic_info"])

            # update_userprofile
            user = User.objects.select_for_update().get(id=self.submission.user_id)
            user_profile = user.userprofile
            user_profile.submission_number += 1
            if quiz.rule_type == QuizRuleType.ACM:
                acm_quizs_status = user_profile.acm_quizs_status.get("quizs", {})
                if quiz_id not in acm_quizs_status:
                    acm_quizs_status[quiz_id] = {"status": self.submission.result, "_id": self.quiz._id}
                    if self.submission.result == JudgeStatus_quiz.CORRECT:
                        user_profile.accepted_number += 1
                elif acm_quizs_status[quiz_id]["status"] != JudgeStatus_quiz.CORRECT:
                    acm_quizs_status[quiz_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus_quiz.CORRECT:
                        user_profile.accepted_number += 1
                user_profile.acm_quizs_status["quizs"] = acm_quizs_status
                user_profile.save(update_fields=["submission_number", "accepted_number", "acm_quizs_status"])

            else:
                oi_quizs_status = user_profile.oi_quizs_status.get("quizs", {})
                score = self.submission.statistic_info["score"]
                if quiz_id not in oi_quizs_status:
                    user_profile.add_score(score)
                    oi_quizs_status[quiz_id] = {"status": self.submission.result,
                                                      "_id": self.quiz._id,
                                                      "score": score}
                    if self.submission.result == JudgeStatus_quiz.CORRECT:
                        user_profile.accepted_number += 1
                elif oi_quizs_status[quiz_id]["status"] != JudgeStatus_quiz.CORRECT:
                    # minus last time score, add this time score
                    user_profile.add_score(this_time_score=score,
                                           last_time_score=oi_quizs_status[quiz_id]["score"])
                    oi_quizs_status[quiz_id]["score"] = score
                    oi_quizs_status[quiz_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus_quiz.CORRECT:
                        user_profile.accepted_number += 1
                user_profile.oi_quizs_status["quizs"] = oi_quizs_status
                user_profile.save(update_fields=["submission_number", "accepted_number", "oi_quizs_status"])

    def update_contest_quiz_status(self):
        with transaction.atomic():
            user = User.objects.select_for_update().get(id=self.submission.user_id)
            user_profile = user.userprofile
            quiz_id = str(self.quiz.id)
            if self.contest.rule_type == ContestRuleType.ACM:
                contest_quizs_status = user_profile.acm_quizs_status.get("contest_quizs", {})
                if quiz_id not in contest_quizs_status:
                    contest_quizs_status[quiz_id] = {"status": self.submission.result, "_id": self.quiz._id}
                elif contest_quizs_status[quiz_id]["status"] != JudgeStatus_quiz.CORRECT:
                    contest_quizs_status[quiz_id]["status"] = self.submission.result
                else:
                    # 如果已AC， 直接跳过 不计入任何计数器
                    return
                user_profile.acm_quizs_status["contest_quizs"] = contest_quizs_status
                user_profile.save(update_fields=["acm_quizs_status"])

            elif self.contest.rule_type == ContestRuleType.OI:
                contest_quizs_status = user_profile.oi_quizs_status.get("contest_quizs", {})
                score = self.submission.statistic_info["score"]
                if quiz_id not in contest_quizs_status:
                    contest_quizs_status[quiz_id] = {"status": self.submission.result,
                                                           "_id": self.quiz._id,
                                                           "score": score}
                else:
                    contest_quizs_status[quiz_id]["score"] = score
                    contest_quizs_status[quiz_id]["status"] = self.submission.result
                user_profile.oi_quizs_status["contest_quizs"] = contest_quizs_status
                user_profile.save(update_fields=["oi_quizs_status"])

            quiz = Quiz.objects.select_for_update().get(contest_id=self.contest_id, id=self.quiz.id)
            result = str(self.submission.result)
            quiz_info = quiz.statistic_info
            quiz_info[result] = quiz_info.get(result, 0) + 1
            quiz.submission_number += 1
            if self.submission.result == JudgeStatus_quiz.CORRECT:
                quiz.accepted_number += 1
            quiz.save(update_fields=["submission_number", "accepted_number", "statistic_info"])

    def update_contest_rank(self):
        if self.contest.rule_type == ContestRuleType.OI or self.contest.real_time_rank:
            cache.delete(f"{CacheKey.contest_rank_cache}:{self.contest.id}")

        def get_rank(model):
            return model.objects.select_for_update().get(user_id=self.submission.user_id, contest=self.contest)

        if self.contest.rule_type == ContestRuleType.ACM:
            model = ACMContestRank
            func = self._update_acm_contest_rank
        else:
            model = OIContestRank
            func = self._update_oi_contest_rank

        try:
            rank = get_rank(model)
        except model.DoesNotExist:
            try:
                model.objects.create(user_id=self.submission.user_id, contest=self.contest)
                rank = get_rank(model)
            except IntegrityError:
                rank = get_rank(model)
        func(rank)

    def _update_acm_contest_rank(self, rank):
        info = rank.submission_info.get(str(self.submission.quiz_id))
        # 因前面更改过，这里需要重新获取
        quiz = Quiz.objects.select_for_update().get(contest_id=self.contest_id, id=self.quiz.id)
        # 此题提交过
        if info:
            if info["is_ac"]:
                return

            rank.submission_number += 1
            if self.submission.result == JudgeStatus_quiz.CORRECT:
                rank.accepted_number += 1
                info["is_ac"] = True
                info["ac_time"] = (self.submission.create_time - self.contest.start_time).total_seconds()
                rank.total_time += info["ac_time"] + info["error_number"] * 20 * 60

                if quiz.accepted_number == 1:
                    info["is_first_ac"] = True
            elif self.submission.result != JudgeStatus_quiz.WROW:
                info["error_number"] += 1

        # 第一次提交
        else:
            rank.submission_number += 1
            info = {"is_ac": False, "ac_time": 0, "error_number": 0, "is_first_ac": False}
            if self.submission.result == JudgeStatus_quiz.CORRECT:
                rank.accepted_number += 1
                info["is_ac"] = True
                info["ac_time"] = (self.submission.create_time - self.contest.start_time).total_seconds()
                rank.total_time += info["ac_time"]

                if quiz.accepted_number == 1:
                    info["is_first_ac"] = True

            elif self.submission.result != JudgeStatus_quiz.WROW:
                info["error_number"] = 1
        rank.submission_info[str(self.submission.quiz_id)] = info
        rank.save()

    def _update_oi_contest_rank(self, rank):
        quiz_id = str(self.submission.quiz_id)
        current_score = self.submission.statistic_info["score"]
        last_score = rank.submission_info.get(quiz_id)
        if last_score:
            rank.total_score = rank.total_score - last_score + current_score
        else:
            rank.total_score = rank.total_score + current_score
        rank.submission_info[quiz_id] = current_score
        rank.save()
