# Enterprise HRMS/CRM/PMS Backend

A comprehensive enterprise backend system built with FastAPI and MySQL, covering HRMS, CRM, and Project Management.

## 🌟 Key Features

- **🔐 Role-Based Access Control (RBAC)**
  - **6 Distinct Roles**: Super Admin, Admin, Manager, HR, Employee, Client.
  - **Granular Permissions**: 35+ specific permissions managing access to every module.
- **👥 Employee Management**: Auto-generated employee IDs (`AW0001`), hierarchy tracking.
- **⏰ Attendance & Leave**: Geo-fenced clock-ins (Office/WFH/Remote), leave balances, approval workflows.
- **💼 Payroll**: Salary plotting, payslip generation.
- **📊 Project Management**: Projects, tasks, sprints, time-tracking.
- **📝 Blog & CMS**: Rich text content, FAQs, categories, authors, and SEO metadata.
- **📈 Reporting**: Custom dashboards for HR and Admin.

## 🛡️ Roles & Permissions (RBAC)

The system creates the following roles by default:

| Role | Access Level | Description |
| :--- | :--- | :--- |
| **Super Admin** | Full Access | Can manage everything including system settings and other admins. |
| **Admin** | High Access | Manages day-to-day operations, employees, and projects. No system config access. |
| **Manager** | Medium Access | Manages their team's tasks and approves leave/attendance. |
| **HR** | Specialized | Focuses on recruitment, payroll, and employee records. |
| **Employee** | Personal | Can view own tasks, request leave, and mark attendance. |
| **Client** | Restricted | Read-only access to their specific project progress and invoices. |

## 🚀 Quick Start (Development)

1. **Setup Environment**

    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

2. **Configure `.env`**
    Copy `.env.example` to `.env` and set your MySQL credentials.

3. **Initialize Database**

    ```bash
    # Create DB 'enterprise_hrms' in MySQL first, then:
    alembic upgrade head
    ```

4. **Run Server**

    ```bash
    uvicorn app.main:app --reload
    ```

    API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

5. **Seed Data** (Optional)

    ```bash
    python seed.py
    ```

## 📦 Production Deployment

 This guide outlines the steps to deploy the Enterprise HRMS/CRM/PMS application in a production environment.

### 1. Prerequisites

- **Server**: Linux (Ubuntu 22.04+ recommended) or Windows Server.
- **Database**: MySQL 8.0+ running and accessible.
- **Runtime**:
  - Node.js 18+ (for Frontend)
  - Python 3.11+ (for Backend)
- **Reverse Proxy**: Nginx (recommended) or Apache.
- **Process Manager**: PM2 (recommended for both frontend/backend) or Systemd/Supervisor.

### 2. Backend Deployment

#### 2.1 Set up Environment

1. Navigate to the backend directory:

    ```bash
    cd backend
    ```

2. Create a virtual environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    pip install gunicorn  # Required for production serving
    ```

#### 2.2 Configure Settings

1. Create a `.env` file based on `.env.example`:

    ```bash
    cp .env.example .env
    ```

2. Update critical production values in `.env`:

    ```ini
    DEBUG=false
    ENVIRONMENT=production
    DATABASE_URL=mysql+pymysql://user:password@localhost/db_name
    SECRET_KEY=<long-random-secure-string>
    CORS_ORIGINS=["https://your-domain.com"]
    ```

#### 2.3 Database Migration

Run Alembic to ensure your database schema is up to date:

```bash
alembic upgrade head
```

#### 2.4 Run with Gunicorn

Do not use `uvicorn --reload` in production. Use Gunicorn with Uvicorn workers:

```bash
# Run on port 8000
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

*Note: `-w 4` specifies 4 worker processes. Adjust based on your CPU cores (usually 2 x CORES + 1).*

### 3. Frontend Deployment

#### 3.1 Build the Application

1. Navigate to the frontend directory:

    ```bash
    cd frontend
    ```

2. Install dependencies:

    ```bash
    npm install
    ```

3. Set up Environment:
    Create `.env.local`:

    ```ini
    NEXT_PUBLIC_API_URL=https://api.your-domain.com/api/v1
    ```

4. Build the Next.js app:

    ```bash
    npm run build
    ```

#### 3.2 Run the Server

You can run the Next.js production server using `npm start`, but it's best managed with PM2.

```bash
npm start
# Runs on localhost:3000 by default
```

### 4. Process Management (PM2)

Use PM2 to keep your applications running in the background and restart them on failure.

1. Install PM2:

    ```bash
    npm install -g pm2
    ```

2. Start Backend:

    ```bash
    cd backend
    pm2 start "gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000" --name "backend-api"
    ```

3. Start Frontend:

    ```bash
    cd frontend
    pm2 start npm --name "frontend-ui" -- start
    ```

4. Save config to restart on reboot:

    ```bash
    pm2 save
    pm2 startup
    ```

### 5. Nginx Configuration (Reverse Proxy)

Set up Nginx to serve requests on port 80/443 and proxy them to your apps.

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}


### Update Database
To apply all pending database changes (migrations):

```bash
alembic upgrade head
```

## 📚 API Endpoints Overview

### Authentication

- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Get Current User Profile

### Employees

- `GET /api/v1/employees` - List employees
- `POST /api/v1/employees` - Create employee (Auto-generates `AW0001` ID)
- `GET /api/v1/employees/{id}` - Get details
- `PUT /api/v1/employees/{id}` - Update details

### Attendance

- `POST /api/v1/attendance/check-in` - Daily Check-in
- `POST /api/v1/attendance/check-out` - Daily Check-out
- `GET /api/v1/attendance/my-summary` - View personal attendance

## 🆔 Employee ID Format

Employees are automatically assigned codes in the format: `AW0001`, `AW0002`, etc.
The prefix can be customized in `.env`:

```ini
EMPLOYEE_ID_PREFIX=AW
EMPLOYEE_ID_LENGTH=4
```

## 🔑 Default Credentials (Seed Data)

These users are created by `python seed.py`:

- **Super Admin**: `admin@demo.com` / `admin123`
- **Admin**: `admin2@demo.com` / `admin123`
- **Manager**: `manager@demo.com` / `manager123`
- **HR**: `hr@demo.com` / `hr123`
- **Employee**: `employee@demo.com` / `employee123`
- **Client**: `client@demo.com` / `client123`

## 🛠️ Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: MySQL 8.0 (SQLAlchemy ORM + Alembic)
- **Auth**: JWT (OAuth2 password flow)
- **Validation**: Pydantic v2
- **Testing**: Pytest

## 📂 Project Structure

```
backend/
├── app/
│   ├── api/v1/           # API Endpoints
│   ├── core/             # Security (RBAC, Middleware)
│   ├── models/           # SQLAlchemy Database Models
│   ├── schemas/          # Pydantic Schemas
│   └── services/         # Business Logic
├── migrations/           # Database Versions
├── alembic.ini           # Migration Config
└── requirements.txt
```
