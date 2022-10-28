from django.conf.urls import url

from ..views.admin import SubmissionRejudgeAPI, SubmissionRejudgeAPI_quiz

urlpatterns = [
    url(r"^submission/rejudge?$", SubmissionRejudgeAPI.as_view(), name="submission_rejudge_api"),
    url(r"^submission/rejudge_quiz?$", SubmissionRejudgeAPI_quiz.as_view(), name="submission_rejudge_api_quiz"),
]
