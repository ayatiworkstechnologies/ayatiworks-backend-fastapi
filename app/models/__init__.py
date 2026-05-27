"""Models package."""

# Import all models so SQLAlchemy relationships and metadata register consistently.
from app.models import ai_bot  # noqa: F401
from app.models import attendance  # noqa: F401
from app.models import auth  # noqa: F401
from app.models import blog  # noqa: F401
from app.models import calendar  # noqa: F401
from app.models import client  # noqa: F401
from app.models import client_module  # noqa: F401
from app.models import communication  # noqa: F401
from app.models import company  # noqa: F401
from app.models import employee  # noqa: F401
from app.models import hr_advanced  # noqa: F401
from app.models import invoice  # noqa: F401
from app.models import leave  # noqa: F401
from app.models import media  # noqa: F401
from app.models import meta  # noqa: F401
from app.models import notification  # noqa: F401
from app.models import organization  # noqa: F401
from app.models import payroll  # noqa: F401
from app.models import project  # noqa: F401
from app.models import public  # noqa: F401
from app.models import report  # noqa: F401
from app.models import security  # noqa: F401
from app.models import settings  # noqa: F401
from app.models import sprint  # noqa: F401
from app.models import team  # noqa: F401
from app.models import ticket  # noqa: F401

