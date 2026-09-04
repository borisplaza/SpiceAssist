# SpiceAssist - Proyecto final de Inteligencia Artificial

Asistente conversacional inteligente para un distribuidor B2B de especias. El prototipo clasifica intenciones, responde FAQs, registra interacciones y solicitudes en SQLite en tiempo real y mantiene revisión humana para cotizaciones, fechas, documentos sensibles e incidencias.

## Ejecutar
1. Tener Python 3.10+ instalado.
2. Abrir una terminal en esta carpeta.
3. Ejecutar: `python app.py`
4. Abrir: `http://127.0.0.1:8000`

No requiere paquetes externos.

## Pruebas sugeridas
- `Necesito una cotización de comino molido por 500 lb`
- `¿Qué documentos pueden acompañar una exportación?`
- `Quiero conocer el estado de la orden SO34180`
- `Tengo una incidencia de calidad y necesito soporte`
- Ingresar un número de tarjeta ficticio para mostrar el control de datos sensibles.

## Evidencia de persistencia
Abrir `data/spiceassist.db` con DB Browser for SQLite, o visitar `http://127.0.0.1:8000/api/requests` para visualizar las últimas solicitudes registradas.

## Componentes críticos para la defensa
- `classify_intent()`: clasificación de la intención mediante coincidencia ponderada y similitud textual.
- `create_request_if_needed()` + `sqlite3`: automatización de persistencia en tiempo real.
- `detect_sensitive()`: control preventivo para evitar registrar identificadores financieros sensibles.

## Nota académica
El catálogo y las políticas del prototipo son simulados. Antes de un uso real deben conectarse a fuentes autorizadas y vigentes del negocio.
