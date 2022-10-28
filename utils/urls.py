from django.conf.urls import url

from .views import SimditorImageUploadAPIView, SimditorFileUploadAPIView, SimditorImageUploadAPIView_quiz, SimditorFileUploadAPIView_quiz

urlpatterns = [
    url(r"^upload_image/?$", SimditorImageUploadAPIView.as_view(), name="upload_image"),
    url(r"^upload_file/?$", SimditorFileUploadAPIView.as_view(), name="upload_file"),
    url(r"^upload_quiz_image/?$", SimditorImageUploadAPIView_quiz.as_view(), name="upload_image"),
    url(r"^upload_quiz_file/?$", SimditorFileUploadAPIView_quiz.as_view(), name="upload_file")
]
