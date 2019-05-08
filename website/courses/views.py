from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from courses.models import Course, Lecture, Semester


class CoursesView(TemplateView):
    """View to display the lectures for a course."""

    template_name = 'courses/index.html'

    def get_context_data(self, year: int, season: str, **kwargs):
        """
        Overridden get_context_data method to add a list of courses and lectures to the template.

        :return: New context.
        """
        context = super(CoursesView, self).get_context_data(**kwargs)

        context['lecture_semester'] = get_object_or_404(Semester, year=year, season=season)

        courses = {}
        for course_name in Course.objects.values_list('name', flat=True):
            courses[course_name] = (
                Lecture
                .objects
                .filter(course__name=course_name, semester__year=year, semester__season=season)
                .order_by(f'date')
            )

        context['courses'] = courses.items()
        return context
