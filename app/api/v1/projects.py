"""
Project and Task API routes.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import PermissionChecker, get_current_active_user, get_db
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.models.auth import User
from app.models.employee import Employee
from app.models.project import Milestone, Project, ProjectMember, Task
from app.models.sprint import TimeEntry
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.project import (
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
    TimeEntryCreate,
    TimeEntryResponse,
)
from app.services.employee_service import EmployeeService

router = APIRouter(tags=["Projects & Tasks"])


# ============== Project Endpoints ==============

@router.get("/projects", response_model=PaginatedResponse[ProjectListResponse])
async def list_projects(
    client_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("project.view")),
    db: Session = Depends(get_db)
):
    """List all projects."""
    query = db.query(Project).options(
        joinedload(Project.client)
    ).filter(Project.is_deleted == False)

    # Filter projects based on permissions
    from app.core.permissions import PermissionCode

    user_permissions = []
    if current_user.role and current_user.role.permissions:
        user_permissions = [p.permission.code for p in current_user.role.permissions if p.permission]

    # If user doesn't have view_all permission and is not super admin, show only assigned projects
    if (PermissionCode.SUPER_ADMIN.value not in user_permissions and
        PermissionCode.PROJECT_VIEW_ALL.value not in user_permissions):

        # Get employee ID
        emp_service = EmployeeService(db)
        employee = emp_service.get_by_user_id(current_user.id)

        if not employee:
            return PaginatedResponse.create([], 0, page, page_size)

        # Filter projects where user is a member OR manager
        query = query.filter(
            (Project.members.any(employee_id=employee.id)) |
            (Project.manager_id == employee.id)
        )

    if client_id:
        query = query.filter(Project.client_id == client_id)

    if status:
        query = query.filter(Project.status == status)

    if search:
        query = query.filter(
            Project.name.ilike(f"%{search}%") |
            Project.code.ilike(f"%{search}%")
        )

    total = query.count()

    offset = (page - 1) * page_size
    projects = query.offset(offset).limit(page_size).all()

    items = []
    for p in projects:
        items.append(ProjectListResponse(
            id=p.id,
            name=p.name,
            code=p.code,
            client_name=p.client.name if p.client else None,
            status=p.status,
            progress=p.progress,
            start_date=p.start_date,
            end_date=p.end_date
        ))

    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(PermissionChecker("project.view")),
    db: Session = Depends(get_db)
):
    """Get project by ID."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    response = ProjectResponse.model_validate(project)
    response.client_name = project.client.name if project.client else None
    response.task_count = len([t for t in project.tasks if not t.is_deleted])

    return response


@router.get("/projects/next-code")
async def get_next_project_code(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the next available project code in sequence (PRJ001, PRJ002, etc.)."""
    # Get all project codes that match PRJ pattern
    projects = db.query(Project.code).filter(
        Project.code.like("PRJ%"),
        Project.is_deleted == False
    ).all()

    max_num = 0
    for (code,) in projects:
        try:
            # Extract number from code like PRJ001, PRJ002
            num_part = code.replace("PRJ", "").lstrip("0")
            if num_part.isdigit():
                num = int(num_part)
                if num > max_num:
                    max_num = num
        except Exception:
            continue

    # Generate next code
    next_num = max_num + 1
    next_code = f"PRJ{next_num:03d}"

    return {"next_code": next_code}


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(PermissionChecker("project.create")),
    db: Session = Depends(get_db)
):
    """Create a new project."""
    # Check if code exists
    existing = db.query(Project).filter(Project.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project code already exists"
        )

    project = Project(
        **data.model_dump(),
        created_by=current_user.id
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: User = Depends(PermissionChecker("project.edit")),
    db: Session = Depends(get_db)
):
    """Update a project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    project.updated_by = current_user.id
    db.commit()
    db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: int,
    current_user: User = Depends(PermissionChecker("project.delete")),
    db: Session = Depends(get_db)
):
    """Delete a project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    project.soft_delete(current_user.id)
    db.commit()

    return MessageResponse(message="Project deleted successfully")



# ============== Project Member Endpoints ==============

from app.schemas.project import ProjectMemberCreate, ProjectMemberResponse


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_project_members(
    project_id: int,
    current_user: User = Depends(PermissionChecker("project.view")),
    db: Session = Depends(get_db)
):
    """List members of a project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    items = []
    for member in project.members:
        if member.left_at:
            continue

        item = ProjectMemberResponse.model_validate(member)
        if member.employee and member.employee.user:
            item.employee_name = f"{member.employee.user.first_name} {member.employee.user.last_name or ''}"
            item.employee_email = member.employee.user.email
        else:
            item.employee_name = "Unknown"
        items.append(item)

    return items


@router.post("/projects/{project_id}/members", response_model=ProjectMemberResponse)
async def add_project_member(
    project_id: int,
    data: ProjectMemberCreate,
    current_user: User = Depends(PermissionChecker("project.edit")),
    db: Session = Depends(get_db)
):
    """Add a member to the project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    # Check if already a member
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.employee_id == data.employee_id,
        ProjectMember.left_at is None
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee is already a member of this project"
        )

    member = ProjectMember(
        project_id=project_id,
        employee_id=data.employee_id,
        role=data.role,
        hourly_rate=data.hourly_rate
    )

    db.add(member)
    db.commit()
    db.refresh(member)

    response = ProjectMemberResponse.model_validate(member)
    if member.employee and member.employee.user:
        response.employee_name = f"{member.employee.user.first_name} {member.employee.user.last_name or ''}"
        response.employee_email = member.employee.user.email
    else:
        response.employee_name = "Unknown"

    return response


@router.delete("/projects/{project_id}/members/{employee_id}", response_model=MessageResponse)
async def remove_project_member(
    project_id: int,
    employee_id: int,
    current_user: User = Depends(PermissionChecker("project.edit")),
    db: Session = Depends(get_db)
):
    """Remove a member from the project."""
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.employee_id == employee_id,
        ProjectMember.left_at is None
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this project"
        )

    member.left_at = date.today()
    db.commit()

    return MessageResponse(message="Member removed successfully")


# ============== Task Endpoints ==============

@router.get("/tasks", response_model=PaginatedResponse[TaskResponse])
async def list_tasks(
    project_id: int | None = None,
    assignee_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("task.view")),
    db: Session = Depends(get_db)
):
    """List all tasks with full details."""
    query = db.query(Task).options(
        joinedload(Task.project),
        joinedload(Task.assignee).joinedload(Employee.user)
    ).filter(Task.is_deleted == False)

    # Filter tasks based on permissions
    from app.core.permissions import PermissionCode

    user_permissions = []
    if current_user.role and current_user.role.permissions:
        user_permissions = [p.permission.code for p in current_user.role.permissions if p.permission]

    # If user doesn't have view_all permission and is not super admin, show only relevant tasks
    if (PermissionCode.SUPER_ADMIN.value not in user_permissions and
        PermissionCode.TASK_VIEW_ALL.value not in user_permissions):

        # Get employee ID
        emp_service = EmployeeService(db)
        employee = emp_service.get_by_user_id(current_user.id)

        if not employee:
            return PaginatedResponse.create([], 0, page, page_size)

        # Filter tasks:
        # 1. Assigned to user
        # 2. Reported by user
        # 3. In projects where user is a member
        # 4. In projects where user is manager

        # Get project IDs where user is a member or manager
        member_project_ids = [m.project_id for m in employee.project_memberships if not m.left_at]
        managed_projects = db.query(Project.id).filter(Project.manager_id == employee.id).all()
        managed_project_ids = [p[0] for p in managed_projects]

        allowed_project_ids = list(set(member_project_ids + managed_project_ids))

        from sqlalchemy import or_
        query = query.filter(
            or_(
                Task.assignee_id == employee.id,
                Task.reporter_id == employee.id,
                Task.project_id.in_(allowed_project_ids)
            )
        )

    if project_id:
        query = query.filter(Task.project_id == project_id)

    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)

    if status:
        query = query.filter(Task.status == status)

    if priority:
        query = query.filter(Task.priority == priority)

    total = query.count()

    offset = (page - 1) * page_size
    tasks = query.order_by(Task.due_date).offset(offset).limit(page_size).all()

    items = []
    for t in tasks:
        item = TaskResponse.model_validate(t)
        item.project_name = t.project.name if t.project else None
        item.assignee_name = t.assignee.user.full_name if t.assignee and t.assignee.user else None
        items.append(item)
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/tasks/my-tasks", response_model=list[TaskListResponse])
async def get_my_tasks(
    status: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get tasks assigned to current user."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)

    if not employee:
        return []

    query = db.query(Task).filter(
        Task.assignee_id == employee.id,
        Task.is_deleted == False
    )

    if status:
        query = query.filter(Task.status == status)

    tasks = query.order_by(Task.due_date).limit(50).all()

    items = []
    for t in tasks:
        items.append(TaskListResponse(
            id=t.id,
            title=t.title,
            project_name=t.project.name if t.project else None,
            assignee_name=current_user.full_name,  # We know this is the current user
            status=t.status,
            priority=t.priority,
            due_date=t.due_date
        ))
    return items


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get task by ID."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.is_deleted == False
    ).first()

    if not task:
        raise ResourceNotFoundError("Task", task_id)

    response = TaskResponse.model_validate(task)
    response.project_name = task.project.name if task.project else None
    response.assignee_name = task.assignee.user.full_name if task.assignee and hasattr(task.assignee, 'user') and task.assignee.user else None

    return response


@router.delete("/tasks/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: int,
    current_user: User = Depends(PermissionChecker("task.delete")),
    db: Session = Depends(get_db)
):
    """Delete a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.is_deleted == False
    ).first()

    if not task:
        raise ResourceNotFoundError("Task", task_id)

    task.soft_delete(current_user.id)
    db.commit()

    return MessageResponse(message="Task deleted successfully")


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(PermissionChecker("task.create")),
    db: Session = Depends(get_db)
):
    """Create a new task. Sends notification to assignee if assigned."""
    from app.services.notification_service import NotificationService

    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)

    task = Task(
        **data.model_dump(),
        reporter_id=employee.id if employee else None,
        created_by=current_user.id
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    # Send notification if task is assigned to someone
    if task.assignee_id:
        try:
            assignee = emp_service.get_by_id(task.assignee_id)
            if assignee and assignee.user_id:
                project = db.query(Project).filter(Project.id == task.project_id).first()
                notification_service = NotificationService(db)
                notification_service.notify_task_assigned(
                    assignee_user_id=assignee.user_id,
                    task_title=task.title,
                    project_name=project.name if project else "Unknown Project",
                    assigned_by=f"{current_user.first_name} {current_user.last_name or ''}",
                    priority=task.priority or "normal",
                    task_id=task.id,
                    due_date=str(task.due_date) if task.due_date else None
                )
        except Exception as e:
            import logging
            logging.error(f"Failed to send task assignment notification: {e}")

    return TaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}/status")
async def update_task_status(
    task_id: int,
    new_status: str = Query(..., description="New status: todo, in_progress, in_review, done"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update task status. Admins/Managers can update any task, employees can only update their assigned tasks."""
    from app.core.permissions import PermissionCode

    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.is_deleted == False
    ).first()

    if not task:
        raise ResourceNotFoundError("Task", task_id)

    # Check permissions - get user's permission codes
    user_permissions = []
    if current_user.role and current_user.role.permissions:
        for rp in current_user.role.permissions:
            if rp.permission:
                user_permissions.append(rp.permission.code)

    # Check if user has admin permissions (task.edit, task.view_all, or super_admin)
    is_admin = (
        PermissionCode.SUPER_ADMIN.value in user_permissions or
        PermissionCode.TASK_EDIT.value in user_permissions or
        PermissionCode.TASK_VIEW_ALL.value in user_permissions
    )

    # Employees can only update their assigned tasks
    if not is_admin:
        if not employee:
            raise PermissionDeniedError("Employee profile not found")
        if task.assignee_id != employee.id:
            raise PermissionDeniedError("You can only update status of tasks assigned to you")

    # Validate status
    valid_statuses = ['todo', 'in_progress', 'in_review', 'done']
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    # Update status
    task.status = new_status

    # Mark completed if status is done
    if new_status == 'done' and not task.completed_at:
        task.completed_at = datetime.utcnow()

    task.updated_by = current_user.id
    db.commit()
    db.refresh(task)

    return {"message": "Task status updated successfully", "status": task.status}


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(PermissionChecker("task.edit")),
    db: Session = Depends(get_db)
):
    """Update a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.is_deleted == False
    ).first()

    if not task:
        raise ResourceNotFoundError("Task", task_id)

    update_data = data.model_dump(exclude_unset=True)

    # Mark completed if status changed to done
    if 'status' in update_data and update_data['status'] == 'done' and not task.completed_at:
        task.completed_at = datetime.utcnow()

    for field, value in update_data.items():
        setattr(task, field, value)

    task.updated_by = current_user.id
    db.commit()
    db.refresh(task)

    return TaskResponse.model_validate(task)



# ============== Milestone Endpoints ==============

@router.get("/milestones", response_model=list[MilestoneResponse])
async def list_milestones(
    project_id: int,
    current_user: User = Depends(PermissionChecker("project.view")),
    db: Session = Depends(get_db)
):
    """List milestones for a project."""
    milestones = db.query(Milestone).filter(
        Milestone.project_id == project_id,
        Milestone.is_deleted == False
    ).order_by(Milestone.due_date).all()

    return [MilestoneResponse.model_validate(m) for m in milestones]


@router.post("/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
async def create_milestone(
    data: MilestoneCreate,
    current_user: User = Depends(PermissionChecker("project.edit")),
    db: Session = Depends(get_db)
):
    """Create a new milestone."""
    milestone = Milestone(
        **data.model_dump(),
        created_by=current_user.id
    )

    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    return MilestoneResponse.model_validate(milestone)


@router.put("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: int,
    data: MilestoneUpdate,
    current_user: User = Depends(PermissionChecker("project.edit")),
    db: Session = Depends(get_db)
):
    """Update a milestone."""
    milestone = db.query(Milestone).filter(
        Milestone.id == milestone_id,
        Milestone.is_deleted == False
    ).first()

    if not milestone:
        raise ResourceNotFoundError("Milestone", milestone_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(milestone, field, value)

    milestone.updated_by = current_user.id
    db.commit()
    db.refresh(milestone)

    return MilestoneResponse.model_validate(milestone)


@router.delete("/milestones/{milestone_id}", response_model=MessageResponse)
async def delete_milestone(
    milestone_id: int,
    current_user: User = Depends(PermissionChecker("project.edit")),
    db: Session = Depends(get_db)
):
    """Delete a milestone."""
    milestone = db.query(Milestone).filter(
        Milestone.id == milestone_id,
        Milestone.is_deleted == False
    ).first()

    if not milestone:
        raise ResourceNotFoundError("Milestone", milestone_id)

    milestone.soft_delete(current_user.id)
    db.commit()

    return MessageResponse(message="Milestone deleted successfully")


# ============== Time Entry Endpoints ==============

@router.get("/time-entries", response_model=PaginatedResponse[TimeEntryResponse])
async def list_time_entries(
    project_id: int | None = None,
    task_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("timesheet.view_all")),
    db: Session = Depends(get_db)
):
    """List time entries."""
    query = db.query(TimeEntry).filter(TimeEntry.is_deleted == False)

    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)

    if task_id:
        query = query.filter(TimeEntry.task_id == task_id)

    if from_date:
        query = query.filter(TimeEntry.date >= from_date)

    if to_date:
        query = query.filter(TimeEntry.date <= to_date)

    total = query.count()

    offset = (page - 1) * page_size
    entries = query.order_by(TimeEntry.date.desc()).offset(offset).limit(page_size).all()

    items = [TimeEntryResponse.model_validate(e) for e in entries]
    return PaginatedResponse.create(items, total, page, page_size)


@router.post("/time-entries", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_time_entry(
    data: TimeEntryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Log time entry."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )

    entry = TimeEntry(
        employee_id=employee.id,
        **data.model_dump(),
        created_by=current_user.id
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return TimeEntryResponse.model_validate(entry)

