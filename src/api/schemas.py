from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

class UserCreate(BaseModel):
    email: str
    name: Optional[str] = None

class UserResponse(BaseModel):
    user_id: str
    email: str
    name: Optional[str]
    api_key: Optional[str]
    created_at: datetime
    class Config: from_attributes = True

class TaskBase(BaseModel):
    task_name: str
    context: str
    base_load_score: float
    rule_type: str
    due_date: Optional[date] = None
    mon: bool = False
    tue: bool = False
    wed: bool = False
    thu: bool = False
    fri: bool = False
    sat: bool = False
    sun: bool = False
    interval_days: Optional[int] = None
    anchor_date: Optional[date] = None
    month_day: Optional[int] = None
    nth_in_month: Optional[int] = None
    weekday_mon1: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    task_name: Optional[str] = None
    context: Optional[str] = None
    base_load_score: Optional[float] = None
    active: Optional[bool] = None
    rule_type: Optional[str] = None
    due_date: Optional[date] = None
    mon: Optional[bool] = None
    tue: Optional[bool] = None
    wed: Optional[bool] = None
    thu: Optional[bool] = None
    fri: Optional[bool] = None
    sat: Optional[bool] = None
    sun: Optional[bool] = None
    interval_days: Optional[int] = None
    anchor_date: Optional[date] = None
    month_day: Optional[int] = None
    nth_in_month: Optional[int] = None
    weekday_mon1: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None

class TaskResponse(TaskBase):
    task_id: str
    active: bool
    class Config: from_attributes = True

class TaskDetail(TaskResponse):
    created_at: datetime
    updated_at: datetime

class ExceptionCreate(BaseModel):
    task_id: str
    target_date: date
    exception_type: str
    override_load_value: Optional[float] = None
    notes: Optional[str] = None

class DashboardResponse(BaseModel):
    today: dict
    weekly: dict
    daily_breakdown: List[dict]
    config: dict

class TrendResponse(BaseModel):
    trends: List[dict]

class ContextDistributionResponse(BaseModel):
    distribution: List[dict]
