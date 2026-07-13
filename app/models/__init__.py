"""Models package."""

# Import all models so SQLAlchemy relationships and metadata register consistently.
from app.models import (
    ai_bot,  # noqa: F401
    attendance,  # noqa: F401
    auth,  # noqa: F401
    blog,  # noqa: F401
    calendar,  # noqa: F401
    client,  # noqa: F401
    client_module,  # noqa: F401
    communication,  # noqa: F401
    company,  # noqa: F401
    employee,  # noqa: F401
    hr_advanced,  # noqa: F401
    invoice,  # noqa: F401
    leave,  # noqa: F401
    media,  # noqa: F401
    meta,  # noqa: F401
    notification,  # noqa: F401
    organization,  # noqa: F401
    payroll,  # noqa: F401
    project,  # noqa: F401
    public,  # noqa: F401
    report,  # noqa: F401
    security,  # noqa: F401
    settings,  # noqa: F401
    sprint,  # noqa: F401
    team,  # noqa: F401
    ticket,  # noqa: F401
)

