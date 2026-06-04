from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer, TokenPairSerializer


# ─────────────────────────────────────────────
# MVT views (templates Django — mantidas para admin/debug)
# ─────────────────────────────────────────────

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.get_full_name() or user.username}!')
            return redirect('users:profile')
        messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'users/login.html')


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Você foi desconectado com sucesso.')
    return redirect('users:login')


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            messages.error(request, 'As senhas não coincidem.')
            return render(request, 'users/register.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Nome de usuário já existe.')
            return render(request, 'users/register.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email já registrado.')
            return render(request, 'users/register.html')

        User.objects.create_user(
            username=username, email=email, password=password,
            first_name=request.POST.get('first_name', ''),
            last_name=request.POST.get('last_name', ''),
            role=request.POST.get('role', 'profissional_saude'),
        )
        messages.success(request, 'Usuário criado com sucesso! Faça login.')
        return redirect('users:login')
    return render(request, 'users/register.html')


@login_required
def profile_view(request):
    return render(request, 'users/profile.html', {'user': request.user})


@login_required
@require_http_methods(["GET", "POST"])
def profile_update_view(request):
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


# ─────────────────────────────────────────────
# API JWT endpoints — consumidos pelo frontend React
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """POST /api/v1/auth/login/ — retorna access + refresh tokens e dados do usuário."""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    return Response(TokenPairSerializer.for_user(user), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    """POST /api/v1/auth/register/ — cria usuário e retorna tokens."""
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(TokenPairSerializer.for_user(user), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """POST /api/v1/auth/logout/ — invalida o refresh token."""
    try:
        RefreshToken(request.data.get('refresh')).blacklist()
    except (TokenError, KeyError):
        pass
    return Response({'detail': 'Logout realizado com sucesso.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_me(request):
    """GET /api/v1/auth/me/ — retorna dados do usuário autenticado."""
    return Response(UserSerializer(request.user).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def api_profile_update(request):
    """PATCH /api/v1/auth/me/ — atualiza perfil do usuário autenticado."""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)
