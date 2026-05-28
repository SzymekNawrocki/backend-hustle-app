class DomainError(Exception):
    def __init__(self, detail: str, status_code: int) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class NotFoundError(DomainError):
    def __init__(self, detail: str = "Not found") -> None:
        super().__init__(detail=detail, status_code=404)


class AIServiceError(DomainError):
    """Raised by AIService when the Groq call fails or returns unusable output."""

    def __init__(self, detail: str, status_code: int = 503) -> None:
        super().__init__(detail=detail, status_code=status_code)


class EmailServiceError(DomainError):
    """Raised by EmailService when the Resend call fails."""

    def __init__(self, detail: str = "Email could not be delivered", status_code: int = 503) -> None:
        super().__init__(detail=detail, status_code=status_code)
