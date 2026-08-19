from datetime import date, timedelta
from sqlalchemy import select
from core.db import init_db, session_scope
import hashlib, secrets
from core.models import User
from core.models import FPTK, Candidate, Application, PipelineEvent
from core.logic import compute_deadline, compute_sla_result, derive_filter_category, derive_recruitment_model

def seed_demo():
    init_db()
    with session_scope() as s:
        if not s.scalar(select(User.id).limit(1)):
            for email, name, role, recruiter, password in [("admin@local","System Admin","admin",None,"admin123"),("manager@local","TA Manager","manager",None,"manager123"),("recruiter@local","Demo Recruiter","recruiter","Karin","recruiter123")]:
                salt=secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,200_000)
                s.add(User(email=email,display_name=name,role=role,recruiter_name=recruiter,password_salt=salt.hex(),password_hash=digest.hex()))
    with session_scope() as s:
        if s.scalar(select(FPTK.id).limit(1)): return
        rows=[
            ("DEMO001","Brand Manager - Ready to Eat","PT MACROPRIMA PANGANUTAMA","Commercial","Brand Marketing","Brand","4A","Victor","OP",130),
            ("DEMO002","Area Sales Manager - Jawa Barat","PT JAVA EGG SPECIALITIES","Sales General Trade","Sales Operation","Sales Operation","4A","Brittney","OP",75),
            ("DEMO003","Head of Area - Bengkulu","PT MACROSENTRA NIAGABOGA","Sales General Trade","Sales Operation","Sales Operation","3A","Fiqra","OP",65),
            ("DEMO004","Continuous Improvement Specialist","PT MACROPRIMA PANGANUTAMA","Operation","Manufacturing Excellence","CI","3A","Kasanah","OP",95),
            ("DEMO005","Quality Assurance Staff","PT CISARUA MOUNTAIN DAIRY, TBK","Manufacture Sentul","Quality","QA","2A","Salwa","Closed",28),
            ("DEMO006","Sales Taking Order Staff (Chilled) - Bekasi","PT MACROPRIMA PANGANUTAMA","Sales General Trade","Sales Operation","Sales Operation","2A","Zwei","Closed",20),
            ("DEMO007","Sales Taking Order Staff (Chilled) - Bogor","PT MACROPRIMA PANGANUTAMA","Sales General Trade","Sales Operation","Sales Operation","2A","Omega","OP",40),
            ("DEMO008","Food Service Supervisor","PT MACROSENTRA NIAGABOGA","Commercial","Food Service","Food Service","3A","Brittney","OP",150),
        ]
        for i,r in enumerate(rows):
            kode,pos,bu,dir,div,dep,lvl,pic,status,age=r; fd=date.today()-timedelta(days=age); deadline=compute_deadline(fd,lvl); offer=(fd+timedelta(days=25)) if status=="Closed" else None
            f=FPTK(kode_unik=kode,position=pos,business_unit=bu,directorate=dir,division=div,department=dep,level_fptk=lvl,level_number=int(lvl[0]),pic_recruiter=pic,status=status,fptk_date=fd,filter_category=derive_filter_category(pos,lvl),vacancy=1,sla_days=45 if lvl.startswith('4') else 30,deadline_sla=deadline,offering_date=offer,sla_result=compute_sla_result(status,deadline,offer)); s.add(f); s.flush()
            for j in range(1,4):
                c=Candidate(name=f"Demo Candidate {i+1}-{j}",email=f"demo{i+1}{j}@example.com"); s.add(c); s.flush(); model=derive_recruitment_model(pos,lvl,f.filter_category); a=Application(fptk_id=f.id,candidate_id=c.id,recruiter=pic,model=model,current_stage="HR Interview"); s.add(a); s.flush();
                for stage in ["Sourcing HR","Shortlist CV","Psikotes","HR Interview"]: s.add(PipelineEvent(application_id=a.id,stage=stage,result="LOLOS",event_date=date.today()-timedelta(days=10-j),created_by="seed"))

if __name__=="__main__": seed_demo(); print("Demo seeded")
