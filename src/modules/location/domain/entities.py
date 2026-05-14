from typing import  List
from sqlmodel import SQLModel, Field, Relationship

class Province(SQLModel, table=True):
    code: int = Field(primary_key=True)
    name: str
    codename: str
    division_type: str
    districts: List["District"] = Relationship(back_populates="province")

class District(SQLModel, table=True):
    code: int = Field(primary_key=True)
    name: str
    codename: str
    division_type: str
    province_code: int = Field(foreign_key="province.code")
    province: Province = Relationship(back_populates="districts")
    wards: List["Ward"] = Relationship(back_populates="district")

class Ward(SQLModel, table=True):
    code: int = Field(primary_key=True)
    name: str
    codename: str
    division_type: str
    district_code: int = Field(foreign_key="district.code")
    district: District = Relationship(back_populates="wards")