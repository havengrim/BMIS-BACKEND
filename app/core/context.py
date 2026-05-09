from contextvars import ContextVar

# Set in AuthLoggerMiddleware for every incoming request
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Set in get_current_user dependency after JWT decode
current_user_id_var: ContextVar[str] = ContextVar("current_user_id", default="")
