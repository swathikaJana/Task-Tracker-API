from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import TASK_CACHE_PREFIX, TaskCache
from app.database import get_session
from app.models import Task, TaskStatus
from app.schemas import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _cache(request: Request) -> TaskCache:
    return request.app.state.cache


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    request: Request,
    session: Session = Depends(get_session),
) -> Task:
    task = Task(title=payload.title, description=payload.description)
    session.add(task)
    session.commit()
    session.refresh(task)
    _cache(request).clear_tasks()
    return task


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    request: Request,
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[TaskResponse]:
    cache_key = f"{TASK_CACHE_PREFIX}list:{status_filter or 'all'}:{limit}:{offset}"
    cache = _cache(request)
    cached_tasks = cache.get(cache_key)
    if cached_tasks is not None:
        return [TaskResponse.model_validate(task) for task in cached_tasks]

    query = select(Task)
    if status_filter is not None:
        query = query.where(Task.status == status_filter)
    tasks = session.scalars(
        query.order_by(Task.created_at.desc(), Task.id.desc()).limit(limit).offset(offset)
    ).all()
    results = [TaskResponse.model_validate(task) for task in tasks]
    cache.set(cache_key, [task.model_dump(mode="json") for task in results])
    return results


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> TaskResponse:
    cache_key = f"{TASK_CACHE_PREFIX}item:{task_id}"
    cache = _cache(request)
    cached_task = cache.get(cache_key)
    if cached_task is not None:
        return TaskResponse.model_validate(cached_task)

    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    result = TaskResponse.model_validate(task)
    cache.set(cache_key, result.model_dump(mode="json"))
    return result


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    request: Request,
    session: Session = Depends(get_session),
) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    session.commit()
    session.refresh(task)
    _cache(request).clear_tasks()
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> Response:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()
    _cache(request).clear_tasks()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
