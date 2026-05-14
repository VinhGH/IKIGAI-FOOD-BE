from building_blocks.exceptions import AppException


class UserNotFoundException(AppException):
    def __init__(self, identifier: str = "") -> None:
        super().__init__("USER_NOT_FOUND", f"Không tìm thấy người dùng {identifier}", 404)


class EmailAlreadyExistsException(AppException):
    def __init__(self, email: str) -> None:
        super().__init__("EMAIL_ALREADY_EXISTS", f"Email {email} đã được sử dụng", 409)


class PhoneAlreadyExistsException(AppException):
    def __init__(self, phone: str) -> None:
        super().__init__("PHONE_ALREADY_EXISTS", f"Số điện thoại {phone} đã được sử dụng", 409)


class UserAlreadyActiveException(AppException):
    def __init__(self) -> None:
        super().__init__("USER_ALREADY_ACTIVE", "Tài khoản đã được xác thực", 409)


class UserNotActiveException(AppException):
    def __init__(self) -> None:
        super().__init__("USER_NOT_ACTIVE", "Tài khoản chưa được xác thực email", 403)


class InvalidVerificationCodeException(AppException):
    def __init__(self) -> None:
        super().__init__("INVALID_VERIFICATION_CODE", "Mã xác thực không hợp lệ hoặc đã hết hạn", 400)


class InvalidCredentialsException(AppException):
    def __init__(self) -> None:
        super().__init__("INVALID_CREDENTIALS", "Email hoặc mật khẩu không đúng", 401)


class DefaultAddressNotFoundException(AppException):
    def __init__(self, address_id: int) -> None:
        super().__init__("ADDRESS_NOT_FOUND", f"Không tìm thấy địa chỉ #{address_id}", 404)


class AddressNotFoundException(DefaultAddressNotFoundException):
    pass
