class RouteError(Exception):
    """Base exception for routing errors."""
    pass


class RouteTooLongError(RouteError):
    """Raised when route distance exceeds API limits."""
    pass


class LocationNotRoutableError(RouteError):
    """Raised when location is not on a routable road."""
    pass


class GeocodingError(RouteError):
    """Raised when geocoding fails."""
    pass
