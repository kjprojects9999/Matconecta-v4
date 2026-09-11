from __future__ import annotations
import hashlib, hmac, json, os, random, secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from database import db_ping, init_db, session_scope
from models import Assunto, FundamentoTopico, Questao, Resposta, Sessao, Tentativa, Usuario
from seed import seed

BASE=Path(__file__).resolve().parent; FRONT=BASE.parent/"frontend"
SESSION_DAYS=int(os.getenv("SESSION_DAYS","7"))
SUBJECT_QUIZ_SIZE=10
FOUNDATION_QUIZ_SIZE=15

def now(): return datetime.now(timezone.utc).replace(tzinfo=None)
def norm_name(v:str)->str: return " ".join(v.strip().split()).casefold()
def hash_password(password:str)->str:
    salt=secrets.token_bytes(16); d=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1); return f"scrypt$16384$8$1${salt.hex()}${d.hex()}"
def verify_password(password:str,stored:str)->bool:
    try:
        scheme,n,r,p,salt,digest=stored.split("$")
        if scheme!="scrypt": return False
        d=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=int(n),r=int(r),p=int(p)); return hmac.compare_digest(d.hex(),digest)
    except Exception: return False
def token_hash(token:str)->str: return hashlib.sha256(token.encode()).hexdigest()
def public_user(u:Usuario): return {"id":u.id,"nome":u.nome,"serie":u.serie,"score":u.pontos}

def create_session(db:Session,user_id:int):
    token=secrets.token_urlsafe(48); db.execute(delete(Sessao).where(Sessao.expira_em < now())); db.add(Sessao(token_hash=token_hash(token),usuario_id=user_id,expira_em=now()+timedelta(days=SESSION_DAYS))); db.flush(); return token

def current_user(authorization:str|None=Header(default=None))->Usuario:
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401,"Faça login para continuar.")
    token=authorization.split(" ",1)[1].strip()
    with session_scope() as db:
        u=db.scalar(select(Usuario).join(Sessao).where(Sessao.token_hash==token_hash(token),Sessao.expira_em>now()))
        if not u: raise HTTPException(401,"Sessão expirada. Entre novamente.")
        return u

class RegisterIn(BaseModel): nome:str=Field(min_length=3,max_length=120); serie:int=Field(ge=1,le=3); senha:str=Field(min_length=8,max_length=128)
class LoginIn(BaseModel): nome:str=Field(min_length=1,max_length=120); senha:str=Field(min_length=1,max_length=128)
class AnswerIn(BaseModel): questao_codigo:str=Field(min_length=1,max_length=80); resposta:int=Field(ge=0,le=3)
class AttemptIn(BaseModel): assunto_id:str=Field(min_length=1,max_length=80); respostas:list[AnswerIn]=Field(min_length=1,max_length=60)
class CheckIn(BaseModel): assunto_id:str=Field(min_length=1,max_length=80); questao_codigo:str=Field(min_length=1,max_length=80); resposta:int=Field(ge=0,le=3)

@asynccontextmanager
async def lifespan(_:FastAPI):
    init_db()
    with session_scope() as db:
        if (db.scalar(select(func.count()).select_from(Questao)) or 0)==0: seed()
    yield

app=FastAPI(title="Matconecta API",version="4.0.0",description="Plataforma educacional de matemática.",lifespan=lifespan)
_origins = [x.strip() for x in os.getenv("APP_ORIGINS", "").split(",") if x.strip()]
if not _origins:
    _origins = ["http://127.0.0.1:8000", "http://localhost:8000"]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health():
    try:
        db_ping()
        with session_scope() as db:
            return {"status":"ok","database":"mysql/mariadb","subjects":db.scalar(select(func.count()).select_from(Assunto)) or 0,"questions":db.scalar(select(func.count()).select_from(Questao).where(Questao.assunto_id.is_not(None))) or 0,"foundation_questions":db.scalar(select(func.count()).select_from(Questao).where(Questao.assunto_id.is_(None))) or 0}
    except Exception as e: raise HTTPException(503,"Banco de dados indisponível. Verifique o MySQL/MariaDB e a configuração de DATABASE_URL.") from e

@app.post("/api/auth/register")
def register(data:RegisterIn):
    nome=" ".join(data.nome.strip().split()); normalized=norm_name(nome)
    if not any(c.isalpha() for c in nome): raise HTTPException(400,"Informe um nome válido.")
    with session_scope() as db:
        if db.scalar(select(Usuario).where(Usuario.nome_normalizado==normalized)): raise HTTPException(409,"Já existe uma conta com esse nome.")
        u=Usuario(nome=nome,nome_normalizado=normalized,serie=data.serie,senha_hash=hash_password(data.senha)); db.add(u); db.flush(); token=create_session(db,u.id); return {"token":token,"user":public_user(u)}

@app.post("/api/auth/login")
def login(data:LoginIn):
    normalized=norm_name(data.nome)
    with session_scope() as db:
        u=db.scalar(select(Usuario).where(Usuario.nome_normalizado==normalized))
        if not u or not verify_password(data.senha,u.senha_hash): raise HTTPException(401,"Nome ou senha incorretos.")
        return {"token":create_session(db,u.id),"user":public_user(u)}

@app.post("/api/auth/logout")
def logout(authorization:str|None=Header(default=None),user:Usuario=Depends(current_user)):
    if authorization:
        token=authorization.split(" ",1)[1].strip();
        with session_scope() as db: db.execute(delete(Sessao).where(Sessao.token_hash==token_hash(token),Sessao.usuario_id==user.id))
    return {"ok":True}

@app.get("/api/me")
def me(user:Usuario=Depends(current_user)): return public_user(user)

@app.get("/api/dashboard")
def dashboard(user:Usuario=Depends(current_user)):
    with session_scope() as db:
        rows=db.execute(select(Tentativa,Assunto.titulo,Assunto.ano).outerjoin(Assunto,Assunto.id==Tentativa.assunto_id).where(Tentativa.usuario_id==user.id).order_by(Tentativa.id.desc())).all()
        items=[{"id":a.id,"assunto_id":a.assunto_id or "foundation","acertos":a.acertos,"total":a.total,"percentual":a.percentual,"pontos":a.pontos,"realizado_em":a.realizado_em.isoformat() if a.realizado_em else None,"titulo":title or "Matemática Básica","ano":year} for a,title,year in rows]
        return {"user":public_user(user),"attempts":items[:20],"total_attempts":len(items),"best_percent":max((x["percentual"] for x in items),default=0),"subjects_started":len({x["assunto_id"] for x in items})}

@app.get("/api/years")
def years(user:Usuario=Depends(current_user)):
    with session_scope() as db:
        subjects=db.execute(select(Assunto.ano,func.count(Assunto.id)).group_by(Assunto.ano).order_by(Assunto.ano)).all()
        done=db.execute(select(Assunto.ano,func.count(func.distinct(Tentativa.assunto_id))).join(Tentativa,Tentativa.assunto_id==Assunto.id).where(Tentativa.usuario_id==user.id).group_by(Assunto.ano)).all(); dm=dict(done)
        return [{"year":y,"count":c,"done":dm.get(y,0)} for y,c in subjects]

def theory(row):
    try:return json.loads(row.teoria_json or "{}")
    except json.JSONDecodeError:return {}

@app.get("/api/foundation/topics")
def foundation_topics(_:Usuario=Depends(current_user)):
    with session_scope() as db:
        rows=db.scalars(select(FundamentoTopico).order_by(FundamentoTopico.ordem)).all(); return [{"id":x.id,"titulo":x.titulo,"resumo":x.resumo,"teoria":x.teoria} for x in rows]

@app.get("/api/foundation/topics/{topic_id}")
def foundation_topic(topic_id:str,_:Usuario=Depends(current_user)):
    with session_scope() as db:
        x=db.get(FundamentoTopico,topic_id)
        if not x: raise HTTPException(404,"Tópico não encontrado.")
        return {"id":x.id,"titulo":x.titulo,"resumo":x.resumo,"teoria":x.teoria}

@app.get("/api/subjects")
def subjects(year:int|None=Query(default=None,ge=1,le=3),_:Usuario=Depends(current_user)):
    with session_scope() as db:
        stmt=select(Assunto).order_by(Assunto.ano,Assunto.numero)
        if year: stmt=stmt.where(Assunto.ano==year)
        return [{"id":x.id,"ano":x.ano,"numero":x.numero,"titulo":x.titulo,"resumo":x.resumo,"detalhe":x.detalhe,"teoria":theory(x)} for x in db.scalars(stmt).all()]

@app.get("/api/subjects/{sid}")
def subject(sid:str,_:Usuario=Depends(current_user)):
    with session_scope() as db:
        x=db.get(Assunto,sid)
        if not x: raise HTTPException(404,"Assunto não encontrado.")
        return {"id":x.id,"ano":x.ano,"numero":x.numero,"titulo":x.titulo,"resumo":x.resumo,"detalhe":x.detalhe,"teoria":theory(x)}

def public_question(q:Questao): return {"id":q.codigo,"q":q.enunciado,"options":[q.alternativa_a,q.alternativa_b,q.alternativa_c,q.alternativa_d]}

def load_questions(db:Session,subject_id:str):
    if subject_id=="foundation": return db.scalars(select(Questao).where(Questao.assunto_id.is_(None)).order_by(Questao.indice)).all()
    if not db.get(Assunto,subject_id): raise HTTPException(404,"Assunto não encontrado.")
    return db.scalars(select(Questao).where(Questao.assunto_id==subject_id).order_by(Questao.indice)).all()

@app.get("/api/subjects/{sid}/questions")
def questions(sid:str,_:Usuario=Depends(current_user)):
    with session_scope() as db:
        rows=list(load_questions(db,sid))
        size=FOUNDATION_QUIZ_SIZE if sid=="foundation" else SUBJECT_QUIZ_SIZE
        picked=random.sample(rows,size) if len(rows)>size else rows[:]
        random.shuffle(picked)
        return [public_question(q) for q in picked]

@app.post("/api/attempts/check")
def check(data:CheckIn,_:Usuario=Depends(current_user)):
    with session_scope() as db:
        q=db.get(Questao,data.questao_codigo)
        if not q or (data.assunto_id=="foundation" and q.assunto_id is not None) or (data.assunto_id!="foundation" and q.assunto_id!=data.assunto_id): raise HTTPException(404,"Questão não encontrada.")
        return {"correta":data.resposta==q.resposta_correta,"gabarito":q.resposta_correta,"explicacao":q.explicacao}

@app.post("/api/attempts")
def attempt(data:AttemptIn,user:Usuario=Depends(current_user)):
    with session_scope() as db:
        rows=load_questions(db,data.assunto_id)
        expected={q.codigo:q for q in rows}
        incoming=[a.questao_codigo for a in data.respostas]
        if not incoming or len(incoming)!=len(set(incoming)) or any(c not in expected for c in incoming): raise HTTPException(400,"Responda todas as questões uma única vez.")
        ordered=sorted(data.respostas,key=lambda a:expected[a.questao_codigo].indice)
        correct=sum(a.resposta==expected[a.questao_codigo].resposta_correta for a in ordered); total=len(ordered); percent=round(correct*100/total); points=correct*10
        rec=Tentativa(usuario_id=user.id,assunto_id=None if data.assunto_id=="foundation" else data.assunto_id,foundation=data.assunto_id=="foundation",acertos=correct,total=total,percentual=percent,pontos=points); db.add(rec); db.flush()
        for order,a in enumerate(ordered,1):
            q=expected[a.questao_codigo]; db.add(Resposta(tentativa_id=rec.id,questao_codigo=q.codigo,ordem=order,resposta_usuario=a.resposta,correta=a.resposta==q.resposta_correta))
        user.pontos+=points
        return {"attempt_id":rec.id,"correct":correct,"total":total,"percent":percent,"points":points,"user":public_user(user),"message":"Excelente! Você demonstrou domínio." if percent>=80 else "Bom trabalho! Revise os erros e tente novamente." if percent>=60 else "Use o resultado como diagnóstico: revise a teoria e pratique novamente."}

@app.get("/",include_in_schema=False)
def index(): return FileResponse(FRONT/"index.html")
@app.get("/style.css",include_in_schema=False)
def css(): return FileResponse(FRONT/"style.css",media_type="text/css")
@app.get("/script.js",include_in_schema=False)
def js(): return FileResponse(FRONT/"script.js",media_type="application/javascript")
