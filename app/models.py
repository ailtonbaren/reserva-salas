from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    matricula = db.Column(db.String(20), nullable=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="aluno")
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    reservas = db.relationship("Reserva", back_populates="usuario", lazy=True)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_admin(self):
        return self.perfil == "administrador"

    @property
    def is_active(self):
        return self.ativo


class Sala(db.Model):
    __tablename__ = "salas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    localizacao = db.Column(db.String(120), nullable=False)
    capacidade = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativa = db.Column(db.Boolean, nullable=False, default=True)
    bloqueada = db.Column(db.Boolean, nullable=False, default=False)

    reservas = db.relationship("Reserva", back_populates="sala", lazy=True)
    bloqueios = db.relationship("BloqueioSala", back_populates="sala", lazy=True)

    @property
    def disponivel(self):
        return self.ativa and not self.bloqueada


class Reserva(db.Model):
    __tablename__ = "reservas"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    sala_id = db.Column(db.Integer, db.ForeignKey("salas.id"), nullable=False)
    data = db.Column(db.Date, nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)
    finalidade = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ativa")
    motivo_cancelamento = db.Column(db.String(255), nullable=True)
    cancelada_em = db.Column(db.DateTime, nullable=True)
    criada_em = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    usuario = db.relationship("Usuario", back_populates="reservas")
    sala = db.relationship("Sala", back_populates="reservas")

    @property
    def ativa(self):
        return self.status == "ativa"


class BloqueioSala(db.Model):
    __tablename__ = "bloqueios_sala"

    id = db.Column(db.Integer, primary_key=True)
    sala_id = db.Column(db.Integer, db.ForeignKey("salas.id"), nullable=False)
    data = db.Column(db.Date, nullable=False, index=True)
    data_fim = db.Column(db.Date, nullable=True, index=True)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    sala = db.relationship("Sala", back_populates="bloqueios")


class ConfiguracaoSistema(db.Model):
    __tablename__ = "configuracoes_sistema"

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(80), unique=True, nullable=False, index=True)
    valor = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
