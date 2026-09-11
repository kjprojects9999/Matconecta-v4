from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    serie: Mapped[int] = mapped_column(Integer, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    pontos: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    tentativas: Mapped[list["Tentativa"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    sessoes: Mapped[list["Sessao"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")

class FundamentoTopico(Base):
    __tablename__ = "fundamentos_topicos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(180), nullable=False)
    resumo: Mapped[str] = mapped_column(Text, nullable=False)
    teoria: Mapped[str] = mapped_column(Text, nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questoes: Mapped[list["Questao"]] = relationship(back_populates="fundamento_topico")

class Assunto(Base):
    __tablename__ = "assuntos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    ano: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    titulo: Mapped[str] = mapped_column(String(180), nullable=False)
    resumo: Mapped[str] = mapped_column(Text, nullable=False)
    detalhe: Mapped[str] = mapped_column(Text, nullable=False)
    teoria_json: Mapped[str] = mapped_column(Text, nullable=False)
    questoes: Mapped[list["Questao"]] = relationship(back_populates="assunto", cascade="all, delete-orphan")
    tentativas: Mapped[list["Tentativa"]] = relationship(back_populates="assunto")
    __table_args__ = (UniqueConstraint("ano", "numero", name="uq_assunto_ano_numero"),)

class Questao(Base):
    __tablename__ = "questoes"
    codigo: Mapped[str] = mapped_column(String(80), primary_key=True)
    assunto_id: Mapped[str | None] = mapped_column(ForeignKey("assuntos.id", ondelete="CASCADE"), nullable=True, index=True)
    fundamento_topico_id: Mapped[str | None] = mapped_column(ForeignKey("fundamentos_topicos.id", ondelete="SET NULL"), nullable=True, index=True)
    indice: Mapped[int] = mapped_column(Integer, nullable=False)
    enunciado: Mapped[str] = mapped_column(Text, nullable=False)
    alternativa_a: Mapped[str] = mapped_column(Text, nullable=False)
    alternativa_b: Mapped[str] = mapped_column(Text, nullable=False)
    alternativa_c: Mapped[str] = mapped_column(Text, nullable=False)
    alternativa_d: Mapped[str] = mapped_column(Text, nullable=False)
    resposta_correta: Mapped[int] = mapped_column(Integer, nullable=False)
    explicacao: Mapped[str] = mapped_column(Text, nullable=False)
    assunto: Mapped[Assunto | None] = relationship(back_populates="questoes")
    fundamento_topico: Mapped[FundamentoTopico | None] = relationship(back_populates="questoes")

class Tentativa(Base):
    __tablename__ = "tentativas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    assunto_id: Mapped[str | None] = mapped_column(ForeignKey("assuntos.id", ondelete="SET NULL"), nullable=True, index=True)
    foundation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acertos: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    percentual: Mapped[int] = mapped_column(Integer, nullable=False)
    pontos: Mapped[int] = mapped_column(Integer, nullable=False)
    realizado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    usuario: Mapped[Usuario] = relationship(back_populates="tentativas")
    assunto: Mapped[Assunto | None] = relationship(back_populates="tentativas")
    respostas: Mapped[list["Resposta"]] = relationship(back_populates="tentativa", cascade="all, delete-orphan")

class Resposta(Base):
    __tablename__ = "respostas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tentativa_id: Mapped[int] = mapped_column(ForeignKey("tentativas.id", ondelete="CASCADE"), nullable=False, index=True)
    questao_codigo: Mapped[str] = mapped_column(ForeignKey("questoes.codigo", ondelete="RESTRICT"), nullable=False, index=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    resposta_usuario: Mapped[int] = mapped_column(Integer, nullable=False)
    correta: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tentativa: Mapped[Tentativa] = relationship(back_populates="respostas")

class Sessao(Base):
    __tablename__ = "sessoes"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    expira_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    usuario: Mapped[Usuario] = relationship(back_populates="sessoes")
