from sqlmodel import Session
from vietnam_provinces.legacy import District as LegacyDistrict
from vietnam_provinces.legacy import Province as LegacyProvince
from vietnam_provinces.legacy import Ward as LegacyWard
from src.modules.location.domain.entities import District as DistrictModel
from src.modules.location.domain.entities import Province as ProvinceModel
from src.modules.location.domain.entities import Ward as WardModel

def seed_vietnam_data(engine):
    with Session(engine) as session:
        # Check if already seeded
        if session.get(ProvinceModel, 1): # Kiểm tra mã tỉnh số 1 (Hà Nội)
            return

        # Seed Province
        for p in LegacyProvince.iter_all():
            session.add(ProvinceModel(
                code=int(p.code),
                name=p.name,
                codename=p.codename,
                division_type=p.division_type.value
            ))
        
        # Seed District
        for d in LegacyDistrict.iter_all():
            session.add(DistrictModel(
                code=int(d.code),
                name=d.name,
                codename=d.codename,
                division_type=d.division_type.value,
                province_code=int(d.province_code)
            ))
            
        # Seed Ward (Nên chia nhỏ batch vì >10k dòng)
        for i, w in enumerate(LegacyWard.iter_all()):
            session.add(WardModel(
                code=int(w.code),
                name=w.name,
                codename=w.codename,
                division_type=w.division_type.value,
                district_code=int(w.district_code)
            ))
            if (i + 1) % 1000 == 0:
                session.commit()
        
        session.commit()
