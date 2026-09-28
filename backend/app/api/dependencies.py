from fastapi import Header, HTTPException


def require_bd_manager(x_demo_role: str = Header(default="bd-manager")) -> str:
    if x_demo_role != "bd-manager":
        raise HTTPException(status_code=403, detail="BD Manager role required")
    return x_demo_role
