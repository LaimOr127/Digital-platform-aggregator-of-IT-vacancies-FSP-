// Отдельный файл вместо inline-скрипта: страница проходит строгий CSP (script-src 'self').
window.ui = SwaggerUIBundle({ url: "/api/openapi.json", dom_id: "#swagger-ui", deepLinking: true });
