from sqlmodel import Session
from vietnam_provinces import ProvinceEnum, DistrictEnum, WardEnum
from src.modules.location.domain.entities import Province, District, Ward

def seed_vietnam_data(engine):
    with Session(engine) as session:
        # Check if already seeded
        if session.get(Province, 1): # Kiểm tra mã tỉnh số 1 (Hà Nội)
            return

        # Seed Province
        for p in ProvinceEnum:
            session.add(Province(
                code=p.value.code,
                name=p.value.name,
                codename=p.value.codename,
                division_type=p.value.division_type.value
            ))
        
        # Seed District
        for d in DistrictEnum:
            session.add(District(
                code=d.value.code,
                name=d.value.name,
                codename=d.value.codename,
                division_type=d.value.division_type.value,
                province_code=d.value.province_code
            ))
            
        # Seed Ward (Nên chia nhỏ batch vì >10k dòng)
        for i, w in enumerate(WardEnum):
            session.add(Ward(
                code=w.value.code,
                name=w.value.name,
                codename=w.value.codename,
                division_type=w.value.division_type.value,
                district_code=w.value.district_code
            ))
            if i % 1000 == 0:
                session.commit()
        
        session.commit()