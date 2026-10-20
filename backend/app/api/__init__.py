"""HTTP layer. Routes validate input, call a service, and shape the response.

Rule: routes never import from ``app.db`` or ``app.clients`` directly.
"""
