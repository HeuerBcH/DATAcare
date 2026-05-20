from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import User


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle user login."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.get_full_name() or user.username}!')
            return redirect('users:profile')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    
    return render(request, 'users/login.html')


@login_required
def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'Você foi desconectado com sucesso.')
    return redirect('users:login')


@require_http_methods(["GET", "POST"])
def register_view(request):
    """Handle user registration."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        role = request.POST.get('role', 'patient')
        
        # Validation
        if password != password_confirm:
            messages.error(request, 'As senhas não coincidem.')
            return render(request, 'users/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Nome de usuário já existe.')
            return render(request, 'users/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email já registrado.')
            return render(request, 'users/register.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        
        messages.success(request, 'Usuário criado com sucesso! Faça login.')
        return redirect('users:login')
    
    return render(request, 'users/register.html')


@login_required
def profile_view(request):
    """Display user profile."""
    return render(request, 'users/profile.html', {'user': request.user})


@login_required
@require_http_methods(["GET", "POST"])
def profile_update_view(request):
    """Update user profile."""
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.phone = request.POST.get('phone', request.user.phone)
        request.user.bio = request.POST.get('bio', request.user.bio)
        
        if 'profile_image' in request.FILES:
            request.user.profile_image = request.FILES['profile_image']
        
        request.user.save()
        messages.success(request, 'Perfil atualizado com sucesso!')
        return redirect('users:profile')
    
    return render(request, 'users/profile_update.html', {'user': request.user})
