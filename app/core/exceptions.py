class AIServiceError(Exception):
    """Raised by AIService when the Groq call fails or returns unusable output."""

    def __init__(self, detail: str, status_code: int = 503) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)
