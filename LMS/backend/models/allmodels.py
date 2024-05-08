from django.db import models
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from django.db.models import Q
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
import re
import json
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.validators import (
    MaxValueValidator,
    validate_comma_separated_integer_list,
)
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now
from django.db.models.signals import pre_save
from backend.utils import unique_slug_generator
from .coremodels import User, Customer

class ActivityLog(models.Model):
    message = models.TextField()
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.created_at}]{self.message}"
    
    class Meta:
        db_table = 'activity_log'
    
# -------------------------------------
    # course models
# -------------------------------------
class CourseManager(models.Manager):
    def search(self, query=None):
        queryset = self.get_queryset()
        if query is not None:
            or_lookup = (
                Q(title__icontains=query)
                | Q(summary__icontains=query)
            )
            queryset = queryset.filter(
                or_lookup
            ).distinct()  # distinct() is often necessary with Q lookups
        return queryset
    
class Course(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200, null=False)
    summary = models.TextField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default= False)
    original_course = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    version_number = models.IntegerField(null=True)
    deleted_at = models.DateTimeField(null=True)
    
    objects = CourseManager()

    def __str__(self):
        return self.title
    
    class Meta:
        db_table = 'course'

@receiver(post_save, sender=Course)
def log_save(sender, instance, created, **kwargs):
    verb = "created" if created else "updated"
    ActivityLog.objects.create(message=f"The course '{instance}' has been {verb}.")

@receiver(post_delete, sender=Course)
def log_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(message=f"The course '{instance}' has been deleted.")
    
    
# -------------------------------------
    # course structure models
# -------------------------------------
class CourseStructure(models.Model):
    CONTENT_TYPE = [
        ('reading', 'Reading Material'),
        ('video', 'Video'),
        ('quiz', 'Quiz'),
    ]
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, related_name="course_structure", on_delete=models.CASCADE, null =  False)
    order_number = models.PositiveIntegerField()
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE)
    content_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default= True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)
    
    class Meta:
        db_table = 'course_structure'


# -------------------------------------
    # course register record models
# -------------------------------------
class CourseRegisterRecord(models.Model):
    id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, related_name='registered_courses', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name='registered_costumer', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, auto_now=False, null=True)
    active = models.BooleanField(default= True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
    deleted_at = models.DateTimeField(null=True)
    
    def __str__(self):
        return self.customer.name+" - "+self.course.title
    
    class Meta:
        db_table = 'course_registration_record'
    
# -------------------------------------
    # course enrollment models
# -------------------------------------
class CourseEnrollment(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, related_name='enrollments', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name='enrolled_courses', on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # to ensure that if person's active status i changed after course update , then no signal is send to him about course change
    active = models.BooleanField(default= True)
    deleted_at = models.DateTimeField(null=True)
    
    def __str__(self):
        return self.user.name+"-"+self.course.title
    
    class Meta:
        db_table = 'course_enrollment'

# -------------------------------------
    # upload reading material models
# -------------------------------------

class UploadReadingMaterial(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    courses = models.ManyToManyField(Course, related_name='reading_materials')
    reading_content =models.TextField()
    uploaded_at = models.DateTimeField(auto_now=False, auto_now_add=True, null=True) # needed to passed when material is uploaded for better working
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
    deleted_at = models.DateTimeField(null=True)
    active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'upload_reading_material'
    def delete(self, *args, **kwargs):
        self.reading_content.delete()
        super().delete(*args, **kwargs)
            
@receiver(post_save, sender=UploadReadingMaterial)
def log_save(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            message=f"The file '{instance.title}' has been uploaded to the course '{instance.courses}'."
        )
    else:
        ActivityLog.objects.create(
            message=f"The file '{instance.title}' of the course '{instance.courses}' has been updated."
        )


@receiver(post_delete, sender=UploadReadingMaterial)
def log_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        message=f"The file '{instance.title}' of the course '{instance.courses}' has been deleted."
    )
# -------------------------------------
    # upload video models
# -------------------------------------
    
class UploadVideo(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, unique=True)
    courses = models.ManyToManyField(Course, related_name='video_materials')
    video = models.FileField(
        upload_to="course_videos/",
        help_text="Valid video formats: mp4, mkv, wmv, 3gp, f4v, avi, mp3",
        validators=[
            FileExtensionValidator(["mp4", "mkv", "wmv", "3gp", "f4v", "avi", "mp3"])
        ],
    )
    summary = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now=False, auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
    deleted_at = models.DateTimeField(null=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'upload_video'
    
    def __str__(self):
        return str(self.title)

    def get_absolute_url(self):
        return reverse(
            "video_single", kwargs={"slug": self.courses.slug, "video_slug": self.slug}
        )

    def delete(self, *args, **kwargs):
        self.video.delete()
        super().delete(*args, **kwargs)


def video_pre_save_receiver(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)


pre_save.connect(video_pre_save_receiver, sender=UploadVideo)

@receiver(post_save, sender=UploadVideo)
def log_save(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            message=f"The video '{instance.title}' has been uploaded to the course {instance.courses}."
        )
    else:
        ActivityLog.objects.create(
            message=f"The video '{instance.title}' of the course '{instance.courses}' has been updated."
        )


@receiver(post_delete, sender=UploadVideo)
def log_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        message=f"The video '{instance.title}' of the course '{instance.courses}' has been deleted."
    )

# -------------------------------------
    # Quiz models
# -------------------------------------


CHOICE_ORDER_OPTIONS = (
    ("content", _("Content")),
    ("random", _("Random")),
    ("none", _("None")),
)

class Quiz(models.Model):
    id = models.AutoField(primary_key=True)
    courses = models.ManyToManyField(Course, related_name='quizzes')
    title = models.CharField(verbose_name=_("Title"), max_length=60, blank=False)
    slug = models.SlugField(blank=True, unique=True)
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
        help_text=_("A detailed description of the quiz"),
    )

    
    answers_at_end = models.BooleanField(
        blank=False,
        default=False,
        verbose_name=_("Answers at end"),
        help_text=_(
            "Correct answer is NOT shown after question. Answers displayed at the end."
        ),
    )
    exam_paper = models.BooleanField(
        blank=False,
        default=False,
        verbose_name=_("Exam Paper"),
        help_text=_(
            "If yes, the result of each attempt by a user will be stored. Necessary for marking."
        ),
    )
    single_attempt = models.BooleanField(
        blank=False,
        default=False,
        verbose_name=_("Single Attempt"),
        help_text=_("If yes, only one attempt by a user will be permitted."),
    )
    pass_mark = models.SmallIntegerField(
        blank=True,
        default=50,
        verbose_name=_("Pass Mark"),
        validators=[MaxValueValidator(100)],
        help_text=_("Percentage required to pass exam."),
    )
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True)
    
    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if self.single_attempt is True:
            self.exam_paper = True

        if self.pass_mark > 100:
            raise ValidationError("%s is above 100" % self.pass_mark)
        if self.pass_mark < 0:
            raise ValidationError("%s is below 0" % self.pass_mark)

        super(Quiz, self).save(force_insert, force_update, *args, **kwargs)

    class Meta:
        verbose_name = _("Quiz")
        verbose_name_plural = _("Quizzes")
        db_table = 'quiz'

    def __str__(self):
        return f"Quiz: {self.title}"

    def get_questions(self):
        # return self.questions.all().select_subclasses()
        return self.questions.all()

    @property
    def get_max_score(self):
        return self.get_questions().count()

    def get_absolute_url(self):
        # return reverse('quiz_start_page', kwargs={'pk': self.pk})
        return reverse("quiz_index", kwargs={"course_id": self.courses.id})

def quiz_pre_save_receiver(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)
pre_save.connect(quiz_pre_save_receiver, sender=Quiz)

class Question(models.Model):
    id = models.AutoField(primary_key=True)
    quizzes = models.ManyToManyField(Quiz, related_name='questions')
    figure = models.ImageField(                             
        upload_to="uploads/%Y/%m/%d",
        blank=True,
        null=True,
        verbose_name=_("Figure"),
        help_text=_("Add an image for the question if it's necessary."),
    )
    content = models.CharField(
        max_length=1000,
        blank=False,
        help_text=_("Enter the question text that you want displayed"),
        verbose_name=_("Question"),
    )
    explanation = models.TextField(
        max_length=2000,
        blank=True,
        help_text=_("Explanation to be shown after the question has been answered."),
        verbose_name=_("Explanation"),
    )
    choice_order = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        choices=CHOICE_ORDER_OPTIONS,
        help_text=_(
            "The order in which multi choice choice options are displayed to the user"
        ),
        verbose_name=_("Choice Order"),
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now=False, auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
    deleted_at = models.DateTimeField(null=True)
    
    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        db_table = 'question'

    def __str__(self):
        return self.content
    
    def check_if_correct(self, guess):
        answer = Choice.objects.get(id=guess)

        if answer.correct is True:
            return True
        else:
            return False

    def order_choices(self, queryset):
        if self.choice_order == "content":
            return queryset.order_by("choice")
        if self.choice_order == "random":
            return queryset.order_by("?")
        if self.choice_order == "none":
            return queryset.order_by()
        return queryset

    def get_choices(self):
        return self.order_choices(Choice.objects.filter(question=self))

    def get_choices_list(self):
        return [
            (choice.id, choice.choice)
            for choice in self.order_choices(Choice.objects.filter(question=self))
        ]

    def answer_choice_to_string(self, guess):
        return Choice.objects.get(id=guess).choice

class Choice(models.Model):
    id = models.AutoField(primary_key=True)
    question = models.ForeignKey(
        Question, verbose_name=_("Question"), on_delete=models.CASCADE
    )

    choice = models.CharField(
        max_length=1000,
        blank=False,
        help_text=_("Enter the choice text that you want displayed"),
        verbose_name=_("Content"),
    )
    correct = models.BooleanField(
        blank=False,
        default=False,
        help_text=_("Is this a correct answer?"),
        verbose_name=_("Correct"),
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now=False, auto_now_add=True, null=True)
    deleted_at = models.DateTimeField(null=True)

    def __str__(self):
        return self.choice

    class Meta:
        verbose_name = _("Choice")
        verbose_name_plural = _("Choices")
        db_table = 'choice'
        
@receiver(pre_save, sender=Choice)
def update_question_and_quiz_active_status(sender, instance, **kwargs):
    # Check if the associated question's active field is False
    if instance.question.active == False:
        # Set the question's active field to True
        instance.question.active = True
        instance.question.save()

        # Check if there's a quiz associated with the question
        if instance.question.quizzes.exists():
            # Iterate over each related quiz and update its active field
            for quiz in instance.question.quizzes.all():
                if quiz.active is False:
                    quiz.active = True
                    quiz.save()

class QuizAttemptHistoryManager(models.Manager):
    def new_sitting(self, enrolled_user, quiz, course):
        # if quiz.random_order is True:
        #     question_set = quiz.question_set.all().select_subclasses().order_by("?")
        # else:
        #     question_set = quiz.question_set.all().select_subclasses()
        question_set = quiz.questions.all()

        question_set = [item.id for item in question_set]

        if len(question_set) == 0:
            raise ImproperlyConfigured(
                "Question set of the quiz is empty. Please configure questions properly"
            )

        # if quiz.max_questions and quiz.max_questions < len(question_set):
        #     question_set = question_set[:quiz.max_questions]

        questions = ",".join(map(str, question_set)) + ","

        new_sitting = self.create(
            enrolled_user=enrolled_user,
            quiz=quiz,
            course=course,
            question_list_order=questions,
            unattempted_question=questions,
            incorrect_questions="",
            current_score=0,
            complete=False,
            user_answers="{}",
        )
        return new_sitting

    def user_sitting(self, enrolled_user, quiz, course):
        if (
            quiz.single_attempt is True
            and self.filter(enrolled_user=enrolled_user, quiz=quiz, course=course, complete=True).exists()
        ):
            return False
        try:
            sitting = self.get(enrolled_user=enrolled_user, quiz=quiz, course=course, complete=False)
        except QuizAttemptHistory.DoesNotExist:
            sitting = self.new_sitting(enrolled_user, quiz, course)
        except QuizAttemptHistory.MultipleObjectsReturned:
            sitting = self.filter(enrolled_user=enrolled_user, quiz=quiz, course=course, complete=False)[
                0
            ]
        return sitting

class QuizAttemptHistory(models.Model):
    id = models.AutoField(primary_key=True)
    enrolled_user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, verbose_name=_("Quiz"), on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course, null=True, verbose_name=_("Course"), on_delete=models.CASCADE
    )
    question_list_order = models.CharField(
        max_length=1024,
        verbose_name=_("Question Order"),
        validators=[validate_comma_separated_integer_list],
    )
    unattempted_question = models.CharField(max_length=1024,
        verbose_name=_("UnAttempted Question List"),
        validators=[validate_comma_separated_integer_list],)
    incorrect_questions = models.CharField(
        max_length=1024,
        blank=True,
        verbose_name=_("Incorrect questions"),
        validators=[validate_comma_separated_integer_list],
    )
    current_score = models.IntegerField(verbose_name=_("Current Score"))
    complete = models.BooleanField(
        default=False, blank=False, verbose_name=_("Complete")
    )
    user_answers = models.TextField(
        blank=True, default="{}", verbose_name=_("User Answers")
    )
    start = models.DateTimeField(auto_now_add=True, verbose_name=_("Start"))
    end = models.DateTimeField(null=True, blank=True, verbose_name=_("End"))
    created_at = models.DateTimeField(auto_now=False, auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
    deleted_at = models.DateTimeField(null=True)
    
    objects = QuizAttemptHistoryManager()

    class Meta:
        permissions = (("view_sittings", _("Can see completed exams.")),)
        db_table = 'quiz_attempt_history'

    def get_first_question(self):
        if not self.unattempted_question:
            return False

        first, _ = self.unattempted_question.split(",", 1)
        question_id = int(first)
        # return Question.objects.get_subclass(id=question_id)
        return Question.objects.get(id=question_id)

    def remove_first_question(self):
        if not self.unattempted_question:
            return

        _, others = self.unattempted_question.split(",", 1)
        self.unattempted_question = others
        self.save()

    def add_to_score(self, points):
        self.current_score += int(points)
        self.save()

    @property
    def get_current_score(self):
        return self.current_score

    def _question_ids(self):
        return [int(n) for n in self.question_list_order.split(",") if n]

    @property
    def get_percent_correct(self):
        dividend = float(self.current_score)
        divisor = len(self._question_ids())
        if divisor < 1:
            return 0  # prevent divide by zero error

        if dividend > divisor:
            return 100

        correct = int(round((dividend / divisor) * 100))

        if correct >= 1:
            return correct
        else:
            return 0

    def mark_quiz_complete(self):
        self.complete = True
        self.end = now()
        self.save()

    def add_incorrect_question(self, question):
        if len(self.incorrect_questions) > 0:
            self.incorrect_questions += ","
        self.incorrect_questions += str(question.id) + ","
        if self.complete:
            self.add_to_score(-1)
        self.save()

    @property
    def get_incorrect_questions(self):
        return [int(q) for q in self.incorrect_questions.split(",") if q]

    def remove_incorrect_question(self, question):
        current = self.get_incorrect_questions
        current.remove(question.id)
        self.incorrect_questions = ",".join(map(str, current))
        self.add_to_score(1)
        self.save()

    @property
    def check_if_passed(self):
        return self.get_percent_correct >= self.quiz.pass_mark

    @property
    def result_message(self):
        if self.check_if_passed:
            return f"You have passed this quiz, congratulation"
        else:
            return f"You failed this quiz, give it one chance again."

    def add_user_answer(self, question, guess):
        current = json.loads(self.user_answers)
        current[question.id] = guess
        self.user_answers = json.dumps(current)
        self.save()

    def get_questions(self, with_answers=False):
        question_ids = self._question_ids()
        questions = sorted(
            self.quiz.questions.filter(id__in=question_ids),
            key=lambda q: question_ids.index(q.id),
        )

        if with_answers:
            user_answers = json.loads(self.user_answers)
            for question in questions:
                question.user_answer = user_answers[str(question.id)]

        return questions

    @property
    def questions_with_user_answers(self):
        return {q: q.user_answer for q in self.get_questions(with_answers=True)}

    @property
    def get_max_score(self):
        return len(self._question_ids())

    def progress(self):
        answered = len(json.loads(self.user_answers))
        total = self.get_max_score
        return answered, total

class ProgressManager(models.Manager):
    def new_progress(self, enrolled_user):
        new_progress = self.create(enrolled_user=enrolled_user, score="")
        new_progress.save()
        return new_progress


class Progress(models.Model):
    id = models.AutoField(primary_key=True)
    enrolled_user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.CharField(
        max_length=1024,
        verbose_name=_("Score"),
        validators=[validate_comma_separated_integer_list],
    )

    objects = ProgressManager()

    class Meta:
        verbose_name = _("User Progress")
        verbose_name_plural = _("User progress records")
        db_table = 'progress'

    def update_score(self, question, score_to_add=0, possible_to_add=0):

        if any(
            [
                item is False
                for item in [
                    score_to_add,
                    possible_to_add,
                    isinstance(score_to_add, int),
                    isinstance(possible_to_add, int),
                ]
            ]
        ):
            return _("error"), _("category does not exist or invalid score")

        to_find = re.escape(str(question.quizzes)) + r",(?P<score>\d+),(?P<possible>\d+),"

        match = re.search(to_find, self.score, re.IGNORECASE)

        if match:
            updated_score = int(match.group("score")) + abs(score_to_add)
            updated_possible = int(match.group("possible")) + abs(possible_to_add)

            new_score = ",".join(
                [str(question.quizzes), str(updated_score), str(updated_possible), ""]
            )

            # swap old score for the new one
            self.score = self.score.replace(match.group(), new_score)
            self.save()

        else:
            #  if not present but existing, add with the points passed in
            self.score += ",".join(
                [str(question.quizzes), str(score_to_add), str(possible_to_add), ""]
            )
            self.save()

    def show_exams(self):
        return QuizAttemptHistory.objects.filter(enrolled_user=self.enrolled_user, complete=True).order_by("-end")
    
class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.TextField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True)
    
    class Meta:
        db_table = 'notification'


# score and dashboard related models
class CourseCompletionStatusPerUser(models.Model):
    """
    on started status - completion_status = in_progress_status = False
    in_progress status - completion_status = False, in_progress_status = True
    completed status - completion_status = True, in_progress_status = False
    """
    """should get new instance when course enrollment table get new instance
    """
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'

    STATUS_CHOICES = [
        (NOT_STARTED, 'Not Started'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
    ]
    
    id = models.AutoField(primary_key=True)
    enrolled_user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    # completion_status = models.BooleanField(default=False)
    # in_progress_status = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NOT_STARTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
    deleted_at = models.DateTimeField(null=True)
    active = models.BooleanField(default=True)
    class Meta:
        db_table = 'course_completion_status'
        
class QuizScore(models.Model):
    """
        get instance made when course enrollment table is populated
        get updated for total_score_per_course and completed_quizzes
        
    """
    id = models.AutoField(primary_key=True)
    enrolled_user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    total_quizzes_per_course = models.IntegerField(default=0) # through count of quizzes(active) in a course
    completed_quiz_count = models.IntegerField(default=0) #by default 0
    total_score_per_course = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
    deleted_at = models.DateTimeField(null=True)
    active = models.BooleanField(default=True)
    class Meta:
        db_table = 'quiz_score'

