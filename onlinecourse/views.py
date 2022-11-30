from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Submission, Choice
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'

def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    
    def extract_answers(request):
        submitted_anwsers = []
        for key in request.POST:
            if key.startswith('choice_'):
                value = request.POST[key]
                choice_id = int(value)
                submitted_anwsers.append(choice_id)
        return submitted_anwsers
    
    if request.method != 'POST' or not request.user.is_authenticated:
        return redirect('onlinecourse:course_details', course_id=course_id)
    
    submitted_answers = extract_answers(request)
    
    user = request.user
    course = get_object_or_404(Course, pk=course_id)
    enrollment = Enrollment.objects.create(user=user, course=course, mode='honor')
    
    submission = Submission.objects.create(enrollment=enrollment)
    submission.choices.set(Choice.objects.filter(id__in=submitted_answers))
    submission.save()
    
    return redirect('onlinecourse:result', course_id=course.id, submission_id=submission.id)

# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
def show_exam_result(request, course_id, submission_id):
    # Get course and submission based on their ids
    course = get_object_or_404(Course, id=course_id)
    submission = get_object_or_404(Submission, id=submission_id)
    
    if submission.enrollment.course.id != course.id:
        raise Http404("Submission does not belong to this course")
    
    # Get the selected choice ids from the submission record
    selected_choices_ids = submission.choices.all().values_list('id', flat=True)
    
    # For each selected choice, check if it is a correct answer or not
    questions = []
    
    score = 0
    full_score = 0
    
    for question in course.question_set.all():
        add_score = True
        full_score += question.grade
        
        q_ctx = {'question_text':question.text, 'choices':[]}
        
        for choice in question.choice_set.all():
            if choice.id in selected_choices_ids:
                if choice.indicate:
                    q_ctx['choices'].append(f'<p style="color:green">Correct answer: {choice.text}</p>')
                else:
                    q_ctx['choices'].append(f'<p style="color:red">Wrong answer: {choice.text}</p>')
                    add_score = False
            else:
                if choice.indicate:
                    q_ctx['choices'].append(f'<p style="color:orange">Not selected: {choice.text}</p>')
                    add_score = False
                else:
                    q_ctx['choices'].append(f'<p>{choice.text}</p>')
        
        questions.append(q_ctx)
        if add_score:
            score += question.grade
    
    ctx = {
        'user': submission.enrollment.user,
        'course': course,
        'grade': round(score*100/full_score, 2),
        'questions': questions,
    }
    
    return render(request, 'onlinecourse/exam_result_bootstrap.html', ctx)
           
    



