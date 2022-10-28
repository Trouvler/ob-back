from account.decorators import super_admin_required
from judge.tasks import judge_task, judge_task_quiz
# from judge.dispatcher import JudgeDispatcher
from utils.api import APIView
from ..models import Submission, QuizSubmission


class SubmissionRejudgeAPI(APIView):
    @super_admin_required
    def get(self, request):
        id = request.GET.get("id")
        if not id:
            return self.error("Parameter error, id is required")
        try:
            submission = Submission.objects.select_related("problem").get(id=id, contest_id__isnull=True)
        except Submission.DoesNotExist:
            return self.error("Submission does not exists")
        submission.statistic_info = {}
        submission.save()

        judge_task.send(submission.id, submission.problem.id)
        return self.success()

class SubmissionRejudgeAPI_quiz(APIView):
    @super_admin_required
    def get(self, request):
        id = request.GET.get("id")
        if not id:
            return self.error("Parameter error, id is required")
        try:
            submission = QuizSubmission.objects.select_related("quiz").get(id=id, contest_id__isnull=True)
        except QuizSubmission.DoesNotExist:
            return self.error("Submission does not exists")
        submission.statistic_info = {}
        submission.save()

        judge_task_quiz.send(submission.id, submission.quiz.id)
        return self.success()
