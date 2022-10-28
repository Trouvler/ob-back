import dramatiq

from account.models import User
from submission.models import Submission, QuizSubmission
from judge.dispatcher import JudgeDispatcher
from judge.dispatcher_quiz import JudgeDispatcher_quiz
from utils.shortcuts import DRAMATIQ_WORKER_ARGS


@dramatiq.actor(**DRAMATIQ_WORKER_ARGS())
def judge_task(submission_id, problem_id):
    uid = Submission.objects.get(id=submission_id).user_id
    if User.objects.get(id=uid).is_disabled:
        return
    JudgeDispatcher(submission_id, problem_id).judge()

def judge_task_quiz(submission_id, quiz_id):
    uid = QuizSubmission.objects.get(id=submission_id).user_id
    if User.objects.get(id=uid).is_disabled:
        return
    JudgeDispatcher_quiz(submission_id, quiz_id).judge()