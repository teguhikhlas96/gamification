from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .forms import UserRegistrationForm, UserLoginForm


def login_view(request):
    """View untuk login user"""
    if request.user.is_authenticated:
        # Redirect berdasarkan role jika sudah login
        if request.user.is_admin():
            return redirect('admin_dashboard:dashboard')
        elif request.user.is_player():
            return redirect('player:dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                # Redirect berdasarkan role
                if user.is_admin():
                    return redirect('admin_dashboard:dashboard')
                elif user.is_player():
                    return redirect('player:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    """View untuk register user baru"""
    if request.user.is_authenticated:
        # Redirect berdasarkan role jika sudah login
        if request.user.is_admin():
            return redirect('admin_dashboard:dashboard')
        elif request.user.is_player():
            return redirect('player:dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now login.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def logout_view(request):
    """View untuk logout user"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')
