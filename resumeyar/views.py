from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

@login_required
def dashboard(request):
    return render(request, 'resumeyar/dashboard.html')

@login_required
def my_resumes(request):
    # TODO: Add resume list logic
    return render(request, 'resumeyar/my_resumes.html')

@login_required
def create_resume(request):
    # TODO: Add resume creation logic
    return render(request, 'resumeyar/create_resume.html')

@login_required
def edit_resume(request, resume_id):
    # TODO: Add resume editing logic
    return render(request, 'resumeyar/edit_resume.html')

@login_required
def resume_templates(request):
    # TODO: Add templates list logic
    return render(request, 'resumeyar/templates.html')

@login_required
def settings(request):
    # TODO: Add settings logic
    return render(request, 'resumeyar/settings.html')
