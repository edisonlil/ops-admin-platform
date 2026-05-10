class MessagingError(Exception):
    """Base messaging domain error."""


class MessageNotFound(MessagingError):
    """Raised when a message or recipient cannot be found."""
