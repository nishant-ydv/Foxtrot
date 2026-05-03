"""Pydantic models for Foxtrot API requests and responses."""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class OptimizeRequest(BaseModel):
    """Request to optimize inventory policy for a department."""
    budget: float = Field(..., description="Budget in dollars, e.g. 100000000.0")
    service_target: float = Field(..., ge=0.0, le=100.0, description="Target service level %, e.g. 97.0")
    dept_id: int = Field(..., description="Department ID, e.g. 101 for Men's Shoes")
    season: str = Field(default="Fall/Holiday", description="Season name")


class PolicyConfig(BaseModel):
    """Policy configuration for a segment."""
    segment: str = Field(..., description="Segment ID: A, B, C, or R")
    dcc_pct: float = Field(..., description="Demand-curve coverage (service level) %")
    safety_stock_pct: float = Field(..., description="Safety stock as % of POG capacity")
    reorder_point: int = Field(..., description="Reorder point (units)")
    order_frequency_days: int = Field(..., description="Order frequency in days")
    moq_threshold: int = Field(..., description="Minimum order quantity threshold")
    preseason_allocation_pct: float = Field(..., description="Pre-season budget allocation %")
    inseason_allocation_pct: float = Field(..., description="In-season budget allocation %")
    markdown_reserve_pct: float = Field(..., description="Markdown reserve %")


class OptimizeResponse(BaseModel):
    """Response from optimization endpoint."""
    feasible: bool = Field(..., description="Whether the target is achievable within budget")
    minimum_budget: Optional[float] = Field(None, description="Minimum budget required if not feasible")
    achieved_service: Optional[float] = Field(None, description="Achieved service level % if feasible")
    total_cost: Optional[float] = Field(None, description="Total cost of the policy")
    configs: Optional[Dict[str, PolicyConfig]] = Field(None, description="Policy configs per segment")
    options: Optional[List[str]] = Field(None, description="Options if not feasible: increase_budget, lower_target, show_whats_possible")
    narration: Optional[str] = Field(None, description="LLM-generated trade-off narration")
    dept_id: Optional[int] = Field(None)
    dept_name: Optional[str] = Field(None)


class ScenarioRequest(BaseModel):
    """Request for a what-if scenario."""
    nl_input: str = Field(..., description="Natural language scenario, e.g. 'What if budget drops $3M?'")
    current_policy: Dict[str, Any] = Field(..., description="Current policy configs")
    budget: float = Field(..., description="Current budget")
    service_target: float = Field(..., description="Current service target")
    dept_id: int = Field(...)


class ScenarioResponse(BaseModel):
    """Response from scenario endpoint."""
    feasible: bool
    configs: Optional[Dict[str, PolicyConfig]] = None
    narration: str = Field(..., description="LLM narration of trade-offs")
    budget_change: Optional[float] = None
    service_change: Optional[float] = None


class DecisionRequest(BaseModel):
    """Request for a high-stakes decision framing."""
    decision_context: str = Field(..., description="Description of the decision, e.g. 'Underforecasted holiday by 20%'")
    dept_id: int
    budget: float
    current_service: float


class DecisionOption(BaseModel):
    """A single option for a high-stakes decision."""
    option: str
    description: str
    upside: Optional[float] = None
    downside: Optional[float] = None
    recommendation: bool = False


class DecisionResponse(BaseModel):
    """Response with framed decision options."""
    context: str
    options: List[DecisionOption]
    recommendation: str


class DepartmentInfo(BaseModel):
    """Department information."""
    id: int
    name: str
    category_id: int


class CategoryInfo(BaseModel):
    """Category information."""
    id: int
    name: str


class DepartmentsResponse(BaseModel):
    """Response listing all departments."""
    categories: List[CategoryInfo]
    departments: List[DepartmentInfo]
