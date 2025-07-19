# 🚀 Crear Pull Requests para Disparar Workflows

## ✅ Workflows Configurados

### Frontend
- **Archivo**: `.github/workflows/deploy.yml`
- **Trigger**: Pull Request a rama `dev`
- **Job**: `deploy-dev` - Despliega a entorno de desarrollo

### Backend  
- **Archivo**: `.github/workflows/deploy.yaml`
- **Trigger**: Pull Request a rama `dev`
- **Job**: `deploy_dev` - Despliega a entorno de desarrollo

## 📋 Pasos para Crear Pull Requests

### 1. Frontend Pull Request

1. **Ir a GitHub**: https://github.com/jlcp89/academic-saas-frontend
2. **Crear Pull Request**:
   - Click en "Compare & pull request" en la notificación de la rama `feature/test-deployment`
   - O ir a "Pull requests" → "New pull request"
3. **Configurar PR**:
   - **Base branch**: `dev`
   - **Compare branch**: `feature/test-deployment`
   - **Title**: "Test deployment workflow"
   - **Description**: "Testing deployment via PR to dev branch"
4. **Crear Pull Request**

### 2. Backend Pull Request

1. **Ir a GitHub**: https://github.com/jlcp89/academic-saas-backend
2. **Crear Pull Request**:
   - Click en "Compare & pull request" en la notificación de la rama `feature/test-deployment`
   - O ir a "Pull requests" → "New pull request"
3. **Configurar PR**:
   - **Base branch**: `dev`
   - **Compare branch**: `feature/test-deployment`
   - **Title**: "Test deployment workflow"
   - **Description**: "Testing deployment via PR to dev branch"
4. **Crear Pull Request**

## 🔍 Verificar Workflows

### Enlaces de Actions
- **Frontend**: https://github.com/jlcp89/academic-saas-frontend/actions
- **Backend**: https://github.com/jlcp89/academic-saas-backend/actions

### URLs de Acceso (después del despliegue)
- **Frontend**: http://52.20.22.173:3000
- **Backend**: http://52.20.22.173:8000
- **Admin**: http://52.20.22.173:8000/admin

## 📝 Notas Importantes

1. **Los workflows se ejecutan automáticamente** cuando se crea el Pull Request
2. **Cada commit adicional** al PR dispara un nuevo despliegue
3. **Los secretos deben estar configurados** en ambos repositorios
4. **La instancia EC2 debe estar disponible** en `52.20.22.173`

## 🎯 Próximos Pasos

1. Crear ambos Pull Requests
2. Verificar que los workflows se ejecuten
3. Revisar logs si hay errores
4. Probar las aplicaciones una vez desplegadas
5. Hacer merge de los PRs cuando todo funcione

---

**Estado**: Ramas `feature/test-deployment` creadas y listas para PR 