from enum import Enum

class VerificationCodeType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    TWO_FACTOR = "two_factor"

class UserRole(Enum):
    end_user = "end_user"
    shipper = "shipper"
    admin = "admin"
    store = "store"
    