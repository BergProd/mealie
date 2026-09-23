from fastapi import APIRouter, Depends, HTTPException, status

from mealie.routes._base import BasePublicController, controller
from mealie.schema.response import ErrorResponse
from mealie.schema.user.registration import CreateUserRegistration
from mealie.schema.user.user import UserOut
from mealie.services.event_bus_service.event_bus_service import EventBusService

router = APIRouter(prefix="/register")


@controller(router)
class RegistrationController(BasePublicController):
    event_bus: EventBusService = Depends(EventBusService.as_dependency)

    @router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
    def register_new_user(self, data: CreateUserRegistration):
        # Zpace provisions users via /api/auth/zpace; Mealie self-registration is disabled.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse.respond("User Registration is Disabled"),
        )
