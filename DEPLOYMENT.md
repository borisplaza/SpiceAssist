# Despliegue

El prototipo funciona localmente sin dependencias. Para entregar un enlace público, debe desplegarse en un servicio con almacenamiento persistente.

## Recomendación académica
- Frontend + API: Render, Railway, PythonAnywhere o servidor institucional.
- Base de datos pública: PostgreSQL/Supabase en lugar de SQLite si el hosting no conserva disco.

## Antes de publicar
1. Reemplazar SQLite por PostgreSQL/Supabase si el proveedor usa disco efímero.
2. Mover credenciales a variables de entorno.
3. Activar HTTPS.
4. Limitar `/api/requests` o eliminar esa ruta del despliegue público.
5. Revisar privacidad y retención.

El enlace público no puede generarse sin acceso a una cuenta de hosting del estudiante.
