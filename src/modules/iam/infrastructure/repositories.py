from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, cast

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.iam.domain.entities import Address, User, VerificationCode
from src.modules.iam.domain.ports import (
    AddressRepository,
    RefreshTokenRecord,
    RefreshTokenRepository,
    UserRepository,
)
from src.modules.iam.domain.value_objects import (
    Email,
    FullName,
    HashedPassword,
    Phone,
    UserRole,
    VerificationCodeType,
)
from src.modules.iam.infrastructure.models import (
    AddressModel,
    RefreshTokenModel,
    UserModel,
    VerificationCodeModel,
)


def _require_user_id(user_id: Optional[int]) -> int:
    if user_id is None:
        raise ValueError("user_id is required for persistence")
    return user_id


def _require_db_user_id(user_id: Optional[int]) -> int:
    if user_id is None:
        raise ValueError("user_id is required in stored rows")
    return user_id


class UserRepositoryImpl(UserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = self._base_query().where(self._user_id_column() == user_id)
        return await self._fetch_one(stmt)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = self._base_query().where(self._email_column() == email)
        return await self._fetch_one(stmt)

    async def get_by_phone(self, phone: str) -> Optional[User]:
        stmt = self._base_query().where(self._phone_column() == phone)
        return await self._fetch_one(stmt)

    async def save(self, user: User) -> User:
        if user.id is None:
            model = self._to_model(user, include_children=False)
            self._session.add(model)
            await self._session.flush()

            model.addresses = [
                self._to_address_model(address, model)
                for address in user.addresses
            ]
            model.verification_codes = [
                self._to_verification_code_model(code, model)
                for code in user.verification_codes
            ]

            await self._session.commit()
            model_id = model.id
            if model_id is None:
                raise RuntimeError("UserModel.id was not populated after insert")
            return await self._require_by_id(model_id)

        existing = await self._load_model(user.id)
        if existing is None:
            model = self._to_model(user, include_children=False)
            self._session.add(model)
            await self._session.flush()
            model.addresses = [
                self._to_address_model(address, model)
                for address in user.addresses
            ]
            model.verification_codes = [
                self._to_verification_code_model(code, model)
                for code in user.verification_codes
            ]
            await self._session.commit()
            model_id = model.id
            if model_id is None:
                raise RuntimeError("UserModel.id was not populated after insert")
            return await self._require_by_id(model_id)

        self._apply_user_fields(existing, user)
        await self._sync_addresses(existing, user.addresses)
        await self._sync_verification_codes(existing, user.verification_codes)
        await self._session.commit()
        if existing.id is None:
            raise RuntimeError("UserModel.id was not populated during update")
        return await self._require_by_id(existing.id)

    async def exists_by_email(self, email: str) -> bool:
        stmt = select(exists().where(self._email_column() == email))
        result = await self._session.execute(stmt)
        return bool(result.scalar_one())

    async def exists_by_phone(self, phone: str) -> bool:
        stmt = select(exists().where(self._phone_column() == phone))
        result = await self._session.execute(stmt)
        return bool(result.scalar_one())

    def _base_query(self):
        return (
            select(UserModel)
            .options(
                selectinload(cast(Any, UserModel).addresses),
                selectinload(cast(Any, UserModel).verification_codes),
            )
        )

    async def _fetch_one(self, stmt) -> Optional[User]:
        result = await self._session.execute(stmt)
        model = result.scalars().unique().one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def _require_by_id(self, user_id: int) -> User:
        user = await self.get_by_id(user_id)
        if user is None:
            raise RuntimeError(f"User #{user_id} was not found after persistence")
        return user

    async def _load_model(self, user_id: int) -> Optional[UserModel]:
        result = await self._session.execute(self._base_query().where(self._user_id_column() == user_id))
        return result.scalars().unique().one_or_none()

    @staticmethod
    def _user_id_column():
        return cast(Any, UserModel).__table__.c.id

    @staticmethod
    def _email_column():
        return cast(Any, UserModel).__table__.c.email

    @staticmethod
    def _phone_column():
        return cast(Any, UserModel).__table__.c.phone

    def _apply_user_fields(self, model: UserModel, user: User) -> None:
        model.email = user.email.value
        model.phone = user.phone.value if user.phone else None
        model.full_name = user.full_name.value
        model.hashed_password = user.hashed_password.value
        model.role = user.role.value
        model.is_active = user.is_active
        model.created_at = user.created_at

    async def _sync_addresses(self, model: UserModel, addresses: list[Address]) -> None:
        existing_by_id = {
            address_model.id: address_model
            for address_model in model.addresses
            if address_model.id is not None
        }
        keep_ids: set[int] = set()
        new_models: list[AddressModel] = []

        for address in addresses:
            if address.id is None:
                new_models.append(self._to_address_model(address, model))
                continue

            keep_ids.add(address.id)
            existing = existing_by_id.get(address.id)
            if existing is None:
                new_models.append(self._to_address_model(address, model))
                continue

            self._apply_address_fields(existing, address)

        for address_model in list(model.addresses):
            if address_model.id is not None and address_model.id not in keep_ids:
                await self._session.delete(address_model)

        model.addresses.extend(new_models)

    async def _sync_verification_codes(
        self,
        model: UserModel,
        verification_codes: list[VerificationCode],
    ) -> None:
        existing_by_id = {
            code_model.id: code_model
            for code_model in model.verification_codes
            if code_model.id is not None
        }
        keep_ids: set[int] = set()
        new_models: list[VerificationCodeModel] = []

        for code in verification_codes:
            if code.id is None:
                new_models.append(self._to_verification_code_model(code, model))
                continue

            keep_ids.add(code.id)
            existing = existing_by_id.get(code.id)
            if existing is None:
                new_models.append(self._to_verification_code_model(code, model))
                continue

            self._apply_verification_code_fields(existing, code)

        for code_model in list(model.verification_codes):
            if code_model.id is not None and code_model.id not in keep_ids:
                await self._session.delete(code_model)

        model.verification_codes.extend(new_models)

    def _apply_address_fields(self, model: AddressModel, address: Address) -> None:
        model.user_id = _require_user_id(address.user_id)
        model.address_name = address.address_name
        model.is_default = address.is_default
        model.province_code = address.province_code
        model.district_code = address.district_code
        model.ward_code = address.ward_code
        model.address_detail = address.address_detail

    def _apply_verification_code_fields(
        self,
        model: VerificationCodeModel,
        verification_code: VerificationCode,
    ) -> None:
        model.user_id = _require_user_id(verification_code.user_id)
        model.code = verification_code.code
        model.code_type = verification_code.code_type.value
        model.expires_at = verification_code.expires_at

    def _to_domain(self, model: UserModel) -> User:
        return User(
            id=model.id,
            email=Email(model.email),
            phone=Phone(model.phone) if model.phone is not None else None,
            full_name=FullName(model.full_name),
            hashed_password=HashedPassword(model.hashed_password),
            role=UserRole(model.role),
            is_active=model.is_active,
            created_at=model.created_at,
            addresses=[self._address_to_domain(address) for address in model.addresses],
            verification_codes=[
                self._verification_code_to_domain(code)
                for code in model.verification_codes
            ],
        )

    def _to_model(self, user: User, *, include_children: bool = True) -> UserModel:
        model = UserModel(
            id=user.id,
            email=user.email.value,
            phone=user.phone.value if user.phone else None,
            full_name=user.full_name.value,
            hashed_password=user.hashed_password.value,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
        )
        if include_children:
            model.addresses = [
                self._to_address_model(address, model) for address in user.addresses
            ]
            model.verification_codes = [
                self._to_verification_code_model(code, model)
                for code in user.verification_codes
            ]
        return model

    def _address_to_domain(self, model: AddressModel) -> Address:
        return Address(
            id=model.id,
            user_id=_require_db_user_id(model.user_id),
            address_name=model.address_name,
            is_default=model.is_default,
            province_code=model.province_code,
            district_code=model.district_code,
            ward_code=model.ward_code,
            address_detail=model.address_detail,
        )

    def _to_address_model(
        self,
        address: Address,
        parent_user: UserModel | None = None,
    ) -> AddressModel:
        if parent_user is not None:
            return AddressModel(
                id=address.id,
                user_id=_require_user_id(parent_user.id),
                address_name=address.address_name,
                is_default=address.is_default,
                province_code=address.province_code,
                district_code=address.district_code,
                ward_code=address.ward_code,
                address_detail=address.address_detail,
            )
        return AddressModel(
            id=address.id,
            user_id=_require_user_id(address.user_id),
            address_name=address.address_name,
            is_default=address.is_default,
            province_code=address.province_code,
            district_code=address.district_code,
            ward_code=address.ward_code,
            address_detail=address.address_detail,
        )

    def _verification_code_to_domain(self, model: VerificationCodeModel) -> VerificationCode:
        return VerificationCode(
            id=model.id,
            user_id=_require_db_user_id(model.user_id),
            code=model.code,
            code_type=VerificationCodeType(model.code_type),
            expires_at=model.expires_at,
        )

    def _to_verification_code_model(
        self,
        verification_code: VerificationCode,
        parent_user: UserModel | None = None,
    ) -> VerificationCodeModel:
        if parent_user is not None:
            return VerificationCodeModel(
                id=verification_code.id,
                user_id=_require_user_id(parent_user.id),
                code=verification_code.code,
                code_type=verification_code.code_type.value,
                expires_at=verification_code.expires_at,
            )
        return VerificationCodeModel(
            id=verification_code.id,
            user_id=_require_user_id(verification_code.user_id),
            code=verification_code.code,
            code_type=verification_code.code_type.value,
            expires_at=verification_code.expires_at,
        )


class AddressRepositoryImpl(AddressRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_by_user(self, user_id: int) -> list[Address]:
        stmt = select(AddressModel).where(self._user_id_column() == user_id)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def save(self, address: Address) -> Address:
        if address.id is None:
            model = self._to_model(address)
            self._session.add(model)
            await self._session.commit()
            return self._to_domain(model)

        existing = await self._session.get(AddressModel, address.id)
        if existing is None:
            model = self._to_model(address)
            self._session.add(model)
            await self._session.commit()
            return self._to_domain(model)

        self._apply_fields(existing, address)
        await self._session.commit()
        return self._to_domain(existing)

    async def delete(self, address_id: int) -> None:
        existing = await self._session.get(AddressModel, address_id)
        if existing is None:
            return

        await self._session.delete(existing)
        await self._session.commit()

    def _to_domain(self, model: AddressModel) -> Address:
        return Address(
            id=model.id,
            user_id=_require_db_user_id(model.user_id),
            address_name=model.address_name,
            is_default=model.is_default,
            province_code=model.province_code,
            district_code=model.district_code,
            ward_code=model.ward_code,
            address_detail=model.address_detail,
        )

    def _to_model(self, address: Address) -> AddressModel:
        return AddressModel(
            id=address.id,
            user_id=_require_user_id(address.user_id),
            address_name=address.address_name,
            is_default=address.is_default,
            province_code=address.province_code,
            district_code=address.district_code,
            ward_code=address.ward_code,
            address_detail=address.address_detail,
        )

    def _apply_fields(self, model: AddressModel, address: Address) -> None:
        model.user_id = _require_user_id(address.user_id)
        model.address_name = address.address_name
        model.is_default = address.is_default
        model.province_code = address.province_code
        model.district_code = address.district_code
        model.ward_code = address.ward_code
        model.address_detail = address.address_detail

    @staticmethod
    def _user_id_column():
        return cast(Any, AddressModel).__table__.c.user_id


class RefreshTokenRepositoryImpl(RefreshTokenRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, token: str, user_id: int, expires_at: datetime) -> None:
        model = RefreshTokenModel(
            token=token,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            is_revoked=False,
        )
        self._session.add(model)
        await self._session.commit()

    async def get_by_token(self, token: str) -> Optional[RefreshTokenRecord]:
        stmt = select(RefreshTokenModel).where(self._token_column() == token)
        result = await self._session.execute(stmt)
        model = result.scalars().one_or_none()
        if model is None:
            return None
        return self._to_record(model)

    async def revoke(self, token: str) -> None:
        stmt = select(RefreshTokenModel).where(self._token_column() == token)
        result = await self._session.execute(stmt)
        model = result.scalars().one_or_none()
        if model is None:
            return

        model.is_revoked = True
        await self._session.commit()

    @staticmethod
    def _token_column():
        return cast(Any, RefreshTokenModel).__table__.c.token

    @staticmethod
    def _to_record(model: RefreshTokenModel) -> RefreshTokenRecord:
        return {
            "token": model.token,
            "user_id": model.user_id,
            "expires_at": model.expires_at,
            "is_revoked": model.is_revoked,
        }
