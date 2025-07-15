# 🎓 Academic SaaS - Instrucciones de Configuración

## ✅ Configuración Completada

La aplicación Academic SaaS ha sido configurada exitosamente con las siguientes características:

### 🗄️ Base de Datos
- **Tipo**: SQLite (para desarrollo)
- **Archivo**: `db.sqlite3`
- **Estado**: ✅ Migraciones aplicadas

### 👤 Usuario Administrador
- **Usuario**: `admin`
- **Email**: `admin@academic-saas.com`
- **Contraseña**: `admin123`
- **Rol**: Superadmin

### 🌐 Entorno Virtual
- **Nombre**: `academic_saas_env`
- **Estado**: ✅ Activo y configurado
- **Dependencias**: ✅ Instaladas

## 🚀 Ejecutar la Aplicación

### Opción 1: Script Automático
```bash
./run_app.sh
```

### Opción 2: Manual
```bash
# Activar entorno virtual
source academic_saas_env/bin/activate

# Iniciar servidor
python manage.py runserver 0.0.0.0:8000
```

## 🔗 Enlaces Importantes

Una vez que el servidor esté ejecutándose:

- **🏠 Aplicación Principal**: http://localhost:8000/
- **⚙️ Panel de Administración**: http://localhost:8000/admin/
- **📖 Documentación API (Swagger)**: http://localhost:8000/api/docs/
- **📋 Documentación API (ReDoc)**: http://localhost:8000/api/redoc/
- **🔧 Esquema OpenAPI**: http://localhost:8000/api/schema/

## 🏢 Estructura Multi-Tenant

### Roles de Usuario
1. **Superadmin**: Gestión completa de la plataforma
2. **Admin**: Administración de escuela específica
3. **Professor**: Gestión de clases y calificaciones
4. **Student**: Acceso a cursos y tareas

### Funcionalidades Principales
- ✅ Gestión de escuelas (tenants)
- ✅ Gestión de usuarios por roles
- ✅ Materias y secciones
- ✅ Inscripciones de estudiantes
- ✅ Tareas y entregas
- ✅ Sistema de calificaciones
- ✅ Aislamiento total de datos entre escuelas

## 🔐 Endpoints de API

### Autenticación
- `POST /api/auth/login/` - Iniciar sesión
- `POST /api/auth/refresh/` - Renovar token

### Gestión (Superadmin)
- `GET/POST /api/superadmin/schools/` - Gestionar escuelas
- `GET/POST /api/superadmin/subscriptions/` - Gestionar suscripciones

### Académico
- `GET/POST /api/subjects/` - Materias
- `GET/POST /api/sections/` - Secciones
- `GET/POST /api/enrollments/` - Inscripciones
- `GET/POST /api/assignments/` - Tareas
- `GET/POST /api/submissions/` - Entregas

## 🔧 Comandos Útiles

```bash
# Activar entorno virtual
source academic_saas_env/bin/activate

# Crear nuevo usuario
python manage.py shell
>>> from apps.users.models import User
>>> User.objects.create_user(username='usuario', password='contraseña', role='STUDENT')

# Acceder a shell de Django
python manage.py shell

# Ejecutar tests
python manage.py test

# Crear migraciones (si modificas modelos)
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate
```

## 📝 Notas Importantes

1. **Seguridad**: Cambia la `SECRET_KEY` en producción
2. **Base de Datos**: Para producción, configura PostgreSQL
3. **Archivos Estáticos**: En producción, configura un servidor web
4. **CORS**: Actualiza `CORS_ALLOWED_ORIGINS` según tu frontend

## 🐛 Resolución de Problemas

### Error de Importación
```bash
export PYTHONPATH=/home/jl/school/repos/academic_saas:$PYTHONPATH
```

### Error de Base de Datos
```bash
rm db.sqlite3
python manage.py migrate
```

### Reinstalar Dependencias
```bash
pip install -r requirements.txt --force-reinstall
```

¡La aplicación está lista para usar! 🎉