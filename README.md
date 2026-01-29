# Enterprise HRMS/CRM/PMS Backend

A comprehensive enterprise backend system built with FastAPI and MySQL, covering HRMS, CRM, and Project Management.

## Features

- 🔐 **Authentication & Authorization** - JWT-based auth with 2FA support
- 👥 **Employee Management** - Auto-generated employee IDs (AW0001 format)
- ⏰ **Attendance Tracking** - Office, WFH, and Remote modes with geo-location
- 📅 **Leave Management** - Leave types, balances, approvals
- 💼 **Payroll & HR** - Salary structures, payslips
- 📊 **Project Management** - Projects, tasks, sprints
- 🤝 **Client Management (CRM)** - Leads, deals, invoices
- 📈 **Reporting & Analytics** - Custom reports, dashboards

## Quick Start

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- pip

### Installation

1. **Clone and navigate to project**

   ```bash
   cd "d:\2026\product 1"
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**

   ```bash
   # Edit .env file with your settings
   # Update DATABASE_URL with your MySQL credentials
   ```

5. **Create database**

   ```sql
   CREATE DATABASE enterprise_hrms;
   ```

6. **Run migrations**

   ```bash
   alembic upgrade head
   ```

7. **Start server**

   ```bash
   uvicorn app.main:app --reload
   ```

8. **Access API docs**
   - Swagger UI: <http://localhost:8000/docs>
   - ReDoc: <http://localhost:8000/redoc>

## Project Structure

```
├── app/
│   ├── api/              # API routes
│   │   └── v1/           # v1 endpoints
│   ├── core/             # Security, permissions
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── config.py         # Settings
│   ├── database.py       # DB connection
│   └── main.py           # FastAPI app
├── migrations/           # Alembic migrations
├── requirements.txt
└── .env
```

## API Endpoints

### Authentication

- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/logout` - Logout
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Current user

### Employees

- `GET /api/v1/employees` - List employees
- `POST /api/v1/employees` - Create employee (auto-generates AW0001 ID)
- `GET /api/v1/employees/{id}` - Get employee
- `PUT /api/v1/employees/{id}` - Update employee
- `DELETE /api/v1/employees/{id}` - Delete employee

### Attendance

- `POST /api/v1/attendance/check-in` - Check in
- `POST /api/v1/attendance/check-out` - Check out
- `GET /api/v1/attendance/today` - Today's attendance
- `GET /api/v1/attendance/my-summary` - Attendance summary

## Employee ID Format

Employees are automatically assigned codes in the format:

- `AW0001`, `AW0002`, `AW0003`, etc.

The prefix can be customized in `.env`:

```
EMPLOYEE_ID_PREFIX=AW
EMPLOYEE_ID_LENGTH=4
```

## Development

### Create new migration

```bash
alembic revision --autogenerate -m "description"
```

### Run tests

```bash
pytest tests/ -v
```

## License

Proprietary - All rights reserved.

cd "d:\2026\product 1"
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

# Create MySQL database: enterprise_hrms

# Update .env with your MySQL credentials

alembic upgrade head
uvicorn app.main:app --reload

# Access: <http://localhost:8000/docs>

Super Admin: <admin@demo.com> / admin123
Admin: <admin2@demo.com> / admin123
Manager: <manager@demo.com> / manager123
HR: <hr@demo.com> / hr123
Employee: <employee@demo.com> / employee123
Client: <client@demo.com> / client123
"# ayatiworks-backend-fastapi" 
