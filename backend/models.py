"""Pydantic models for Foxtrot API requests and responses."""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class OptimizeRequest(BaseModel):
    """Request to optimize inventory policy for a department."""
    budget: float = Field(..., description="Budget in dollars, e.g. 100000000.0")
    service_target: float = Field(..., ge=0.0, le=100.0, description="Target service level %, e.g. 97.0")
    dept_id: Optional[int] = Field(None, description="Department ID, e.g. 101 for Men's Shoes (mutually exclusive with dept_ids, category_ids)")
    dept_ids: Optional[List[int]] = Field(None, description="List of department IDs to optimize (mutually exclusive with dept_id, category_ids)")
    category_ids: Optional[List[int]] = Field(None, description="List of category IDs to optimize (mutually exclusive with dept_id, dept_ids)")
    season: str = Field(default="Fall/Holiday", description="Season name")
    return_sku_level: bool = Field(False, description="Return SKU-level policy instead of segment-level")


class PolicyConfig(BaseModel):
    """Policy configuration for a segment."""
    segment: str = Field(..., description="Segment ID: A, B, C, or R")
    dcc_pct: float = Field(..., description="Demand-curve coverage (service level) %")
    safety_stock_pct: float = Field(..., description="Safety stock as % of POG capacity")
    reorder_point: int = Field(..., description="Reorder point (units)")
    order_frequency_days: int = Field(..., description="Order frequency in days")
    moq_threshold: int = Field(..., description="Minimum order quantity threshold (computed as 5% of segment demand)")
    preseason_allocation_pct: float = Field(..., description="Pre-season budget allocation %")
    inseason_allocation_pct: float = Field(..., description="In-season budget allocation %")
    end_of_season_pct: float = Field(..., description="End of season markdown reserve %")


class OptimizeResponse(BaseModel):
    """Response from optimization endpoint."""
    feasible: bool = Field(..., description="Whether the target is achievable within budget")
    minimum_budget: Optional[float] = Field(None, description="Minimum budget required if not feasible")
    achieved_service: Optional[float] = Field(None, description="Achieved service level % if feasible")
    total_cost: Optional[float] = Field(None, description="Total cost of the policy")
    budget_remaining: Optional[float] = Field(None, description="Budget remaining after policy cost")
    budget_remaining_millions: Optional[float] = Field(None, description="Budget remaining in $M")
    markdown_risk: Optional[float] = Field(None, description="Estimated markdown risk ($)")
    sales_loss_risk: Optional[float] = Field(None, description="Estimated sales loss risk if service < target ($)")
    configs: Optional[Dict[str, PolicyConfig]] = Field(None, description="Policy configs per segment")
    per_department_configs: Optional[Dict[int, Dict[str, Any]]] = Field(None, description="Per-department configs for multi-dept/category requests")
    sku_configs: Optional[Dict[str, Any]] = Field(None, description="SKU-level policy configs if requested")
    aggregated_summary: Optional[Dict[str, Any]] = Field(None, description="Aggregated summary for multi-dept/category requests")
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
    explanation: Optional[str] = None
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


class PolicyApprovalRequest(BaseModel):
    """Request to approve a policy."""
    policy_id: str = Field(..., description="ID of policy to approve")
    approver: str = Field(..., description="Approver name or ID")
    approval_notes: Optional[str] = None
    approved_policy: Dict[str, Any] = Field(..., description="The policy configs being approved")


class PolicyApprovalResponse(BaseModel):
    """Response for policy approval."""
    approval_id: str
    status: str = "approved"
    timestamp: str
    approved_policy: Dict[str, Any]
    approver: str
