from rest_framework.permissions import BasePermission


class IsGestor(BasePermission):
    """Gestor/Coordenador de UBS — acesso a dashboards, alertas e configurações da unidade."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'gestor'
        )


class IsACS(BasePermission):
    """Agente Comunitário de Saúde — acesso a formulários de visita e dados de pacientes atribuídos."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'acs'
        )


class IsProfissionalSaude(BasePermission):
    """Profissional de saúde (médico, enfermeiro) — acesso a prontuários e triagem."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'profissional_saude'
        )


class IsAdmin(BasePermission):
    """Administrador do sistema — acesso irrestrito."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class IsGestorOrAdmin(BasePermission):
    """Gestor ou admin — usado em rotas de indicadores e configuração."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('gestor', 'admin')
        )


class IsUBSStaff(BasePermission):
    """Qualquer usuário interno da UBS (gestor, acs, profissional ou admin)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('gestor', 'acs', 'profissional_saude', 'admin')
        )
