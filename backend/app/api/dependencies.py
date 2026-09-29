from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException


@dataclass(frozen=True)
class Principal:
    id: str
    name: str
    role: str


DEMO_USERS = {
    "bd-manager-1": Principal("bd-manager-1", "Meera Raman", "bd-manager"),
    "bd-executive-1": Principal("bd-executive-1", "Arun Kumar", "bd-executive"),
    "bd-executive-2": Principal("bd-executive-2", "Kavya Selvan", "bd-executive"),
    "survey-manager-1": Principal("survey-manager-1", "Priya Natarajan", "survey-manager"),
    "survey-executive-1": Principal("survey-executive-1", "Dinesh Ravi", "survey-executive"),
    "survey-executive-2": Principal("survey-executive-2", "Nila Krishnan", "survey-executive"),
}


def get_principal(
    x_demo_role: str = Header(default="bd-manager"),
    x_demo_user_id: str | None = Header(default=None),
) -> Principal:
    default_id = "bd-manager-1" if x_demo_role == "bd-manager" else "bd-executive-1"
    principal = DEMO_USERS.get(x_demo_user_id or default_id)
    if not principal or principal.role != x_demo_role:
        raise HTTPException(status_code=403, detail="Demo user does not belong to the selected role")
    return principal


def get_authenticated_principal(
    x_demo_role: str = Header(),
    x_demo_user_id: str = Header(),
) -> Principal:
    principal = DEMO_USERS.get(x_demo_user_id)
    if not principal or principal.role != x_demo_role:
        raise HTTPException(status_code=403, detail="Demo user does not belong to the selected role")
    return principal


def require_bd_manager(principal: Annotated[Principal, Depends(get_principal)]) -> str:
    if principal.role != "bd-manager":
        raise HTTPException(status_code=403, detail="BD Manager role required")
    return principal.role


def require_manager_principal(
    principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> Principal:
    if principal.role != "bd-manager":
        raise HTTPException(status_code=403, detail="BD Manager role required")
    return principal


def require_executive_principal(
    principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> Principal:
    if principal.role != "bd-executive":
        raise HTTPException(status_code=403, detail="BD Executive role required")
    return principal


def require_survey_manager_principal(
    principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> Principal:
    if principal.role != "survey-manager":
        raise HTTPException(status_code=403, detail="Survey Manager role required")
    return principal


def require_survey_executive_principal(
    principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> Principal:
    if principal.role != "survey-executive":
        raise HTTPException(status_code=403, detail="Survey Executive role required")
    return principal
