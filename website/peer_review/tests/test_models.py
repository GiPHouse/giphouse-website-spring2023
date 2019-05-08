from courses.models import Semester

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User as DjangoUser
from django.test import TestCase
from django.utils import timezone

from peer_review.models import Answer, Question, Questionnaire, QuestionnaireSubmission

User: DjangoUser = get_user_model()


class PeerReviewTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        semester = Semester.objects.create(
            year=2019,
            season=Semester.SPRING,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timezone.timedelta(days=60)
        )

        cls.questionnaire = Questionnaire.objects.create(
            semester=semester,
            title="An Active Questionnaire",
            available_from=timezone.now() - timezone.timedelta(days=2),
            available_until_soft=timezone.now() + timezone.timedelta(days=1),
            available_until_hard=timezone.now() + timezone.timedelta(days=1),
        )

        user = User.objects.create_user(
            username='Jack',
        )

        cls.submission = QuestionnaireSubmission.objects.create(
            questionnaire_id=cls.questionnaire.id,
            participant=user,
        )

        cls.open_question = Question.objects.create(
            questionnaire=cls.questionnaire,
            question='q1',
            question_type=Question.OPEN,
            about_team_member=False
        )
        cls.quality_question = Question.objects.create(
            questionnaire=cls.questionnaire,
            question='q2',
            question_type=Question.QUALITY,
            about_team_member=False
        )
        cls.agreement_question = Question.objects.create(
            questionnaire=cls.questionnaire,
            question='q3',
            question_type=Question.AGREEMENT,
            about_team_member=False
        )

    def test_set_open_answer(self):
        answer = Answer.objects.create(
            question=self.open_question,
            submission=self.submission,
        )
        self.assertIsNone(answer.answer)
        answer.answer = 'test'
        self.assertEqual(answer.answer, 'test')

    def test_set_agreement_answer(self):
        answer = Answer.objects.create(
            question=self.agreement_question,
            submission=self.submission,
        )
        self.assertIsNone(answer.answer)
        answer.answer = 0
        self.assertEqual(answer.answer, 0)

    def test_set_quality_answer(self):
        answer = Answer.objects.create(
            question=self.quality_question,
            submission=self.submission,
        )
        self.assertIsNone(answer.answer)
        answer.answer = 0
        self.assertEqual(answer.answer, 0)

    def test_open_likert_values(self):
        self.assertEqual(self.open_question.get_likert_choices(), ())
