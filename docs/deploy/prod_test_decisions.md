1. Domaine unique same-origin.
2. HTTPS obligatoire via Cloudflare/proxy.
3. PWA cache shell only ; API/media/network-only.
4. Pas d’offline métier en prod-test.
5. Media privé : photos persistées, audio jamais persisté.
6. WebSocket heartbeat + reconnect obligatoire.
7. Celery-beat obligatoire en prod-test.
8. Backup DB quotidien + backup media privé.