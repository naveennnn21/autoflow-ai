"""AutoFlow AI - Phase 2 AI workflow generation tests.

Covers the non-generated AI workflow surface: the AI runtime
orchestration service (``app.services.ai_runtime``), the pure helpers of
the AI workflow router (``app.api.v1.routers.ai_workflow``), and the
end-to-end generation flow (prompt -> plan -> spec -> runtime ->
execution). Hermetic: no database, no network, no API keys.
"""
