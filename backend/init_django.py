"""
DATAcare Django backend initialization script.
Executa migrations, cria superuser e coleta arquivos estáticos.
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model

def setup():
    print("=" * 50)
    print("DATAcare Django Setup")
    print("=" * 50)
    
    # Run migrations
    print("\n1. Executando migrations...")
    try:
        call_command('migrate', verbosity=1)
        print("✓ Migrations executadas com sucesso")
    except Exception as e:
        print(f"✗ Erro ao executar migrations: {e}")
        return False
    
    # Collect static files
    print("\n2. Coletando arquivos estáticos...")
    try:
        call_command('collectstatic', '--noinput', verbosity=1)
        print("✓ Arquivos estáticos coletados")
    except Exception as e:
        print(f"✗ Erro ao coletar arquivos estáticos: {e}")
        return False
    
    # Create superuser if doesn't exist
    print("\n3. Verificando superusuário...")
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        print("Nenhum superusuário encontrado.")
        print("Criando superusuário 'admin'...")
        try:
            call_command('createsuperuser', 
                        username='admin',
                        email='admin@datacare.local',
                        interactive=False)
            print("✓ Superusuário 'admin' criado")
            print("  Senha: admin123 (MUDE ISSO EM PRODUÇÃO)")
        except Exception as e:
            print(f"⚠ Não foi possível criar superusuário automaticamente: {e}")
            print("  Execute: python manage.py createsuperuser")
    else:
        print("✓ Superusuário já existe")
    
    print("\n" + "=" * 50)
    print("Setup concluído!")
    print("=" * 50)
    print("\nPróximos passos:")
    print("1. Ativar ambiente Python: .venv\\Scripts\\Activate.ps1")
    print("2. Executar servidor: python manage.py runserver")
    print("3. Acessar admin: http://localhost:8000/admin")
    print("=" * 50 + "\n")
    
    return True

if __name__ == '__main__':
    success = setup()
    sys.exit(0 if success else 1)
