from datetime import date, datetime, time, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models import BloqueioSala, ConfiguracaoSistema, Reserva, Sala


class RegraReservaErro(ValueError):
    pass


def obter_configuracao_int(chave, padrao):
    configuracao = ConfiguracaoSistema.query.filter_by(chave=chave).first()
    if not configuracao:
        return padrao
    try:
        return int(configuracao.valor)
    except ValueError:
        return padrao


def definir_configuracao(chave, valor, descricao=None):
    configuracao = ConfiguracaoSistema.query.filter_by(chave=chave).first()
    if not configuracao:
        configuracao = ConfiguracaoSistema(chave=chave, valor=str(valor), descricao=descricao)
        db.session.add(configuracao)
    else:
        configuracao.valor = str(valor)
        if descricao is not None:
            configuracao.descricao = descricao
    db.session.commit()
    return configuracao


def obter_limite_reservas_ativas_aluno():
    return obter_configuracao_int("max_reservas_ativas_aluno", 3)


def obter_ids_salas_bloqueadas_na_data(data):
    bloqueios = BloqueioSala.query.filter(
        BloqueioSala.ativo.is_(True),
        BloqueioSala.data <= data,
        or_(BloqueioSala.data_fim.is_(None), BloqueioSala.data_fim >= data),
    ).all()
    return {bloqueio.sala_id for bloqueio in bloqueios}


def parse_date(value):
    value = (value or "").strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, formato).date()
        except ValueError:
            continue
    raise ValueError("Data inválida. Use o formato dd/mm/aaaa.")


def parse_time(value):
    return datetime.strptime(value, "%H:%M").time()


def horarios_sobrepostos(inicio_a, fim_a, inicio_b, fim_b):
    return inicio_a < fim_b and inicio_b < fim_a


def validar_reserva(usuario, sala, data, hora_inicio, hora_fim, reserva_ignorada_id=None):
    if not sala or not sala.disponivel:
        raise RegraReservaErro("A sala está inativa ou bloqueada e não pode ser reservada.")

    inicio_dt = datetime.combine(data, hora_inicio)
    fim_dt = datetime.combine(data, hora_fim)

    if inicio_dt <= datetime.now():
        raise RegraReservaErro(
            "Não é permitido criar reservas em datas ou horários passados."
        )

    if fim_dt <= inicio_dt:
        raise RegraReservaErro("A hora final deve ser posterior à hora inicial.")

    if (fim_dt - inicio_dt).total_seconds() != 3600:
        raise RegraReservaErro("A reserva deve ter duração de uma hora.")

    if not usuario.is_admin:
        limite = obter_limite_reservas_ativas_aluno()
        reservas_ativas = Reserva.query.filter_by(usuario_id=usuario.id, status="ativa").count()
        if reservas_ativas >= limite:
            raise RegraReservaErro(
                f"Você atingiu o limite de {limite} reservas ativas permitido por aluno."
            )

    query_sala = Reserva.query.filter_by(sala_id=sala.id, data=data, status="ativa")
    if reserva_ignorada_id:
        query_sala = query_sala.filter(Reserva.id != reserva_ignorada_id)

    for reserva in query_sala.all():
        if horarios_sobrepostos(hora_inicio, hora_fim, reserva.hora_inicio, reserva.hora_fim):
            raise RegraReservaErro(
                f"A sala {sala.nome} já está reservada das "
                f"{reserva.hora_inicio.strftime('%H:%M')} às {reserva.hora_fim.strftime('%H:%M')}."
            )

    bloqueios = BloqueioSala.query.filter(
        BloqueioSala.sala_id == sala.id,
        BloqueioSala.ativo.is_(True),
        BloqueioSala.data <= data,
        or_(BloqueioSala.data_fim.is_(None), BloqueioSala.data_fim >= data),
    ).all()
    for bloqueio in bloqueios:
        data_fim = bloqueio.data_fim or bloqueio.data
        raise RegraReservaErro(
            f"A sala {sala.nome} está bloqueada de "
            f"{bloqueio.data.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}. "
            f"Motivo: {bloqueio.motivo}."
        )

    query_usuario = Reserva.query.filter_by(usuario_id=usuario.id, data=data, status="ativa")
    if reserva_ignorada_id:
        query_usuario = query_usuario.filter(Reserva.id != reserva_ignorada_id)

    for reserva in query_usuario.all():
        if horarios_sobrepostos(hora_inicio, hora_fim, reserva.hora_inicio, reserva.hora_fim):
            raise RegraReservaErro(
                "Você já possui uma reserva ativa das "
                f"{reserva.hora_inicio.strftime('%H:%M')} às {reserva.hora_fim.strftime('%H:%M')}."
            )


def criar_reserva(usuario, sala_id, data_str, inicio_str, fim_str, finalidade):
    sala = db.session.get(Sala, int(sala_id))
    data = parse_date(data_str)
    hora_inicio = parse_time(inicio_str)
    hora_fim = parse_time(fim_str)

    validar_reserva(usuario, sala, data, hora_inicio, hora_fim)

    reserva = Reserva(
        usuario_id=usuario.id,
        sala_id=sala.id,
        data=data,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        finalidade=finalidade.strip(),
        status="ativa",
    )
    db.session.add(reserva)
    db.session.commit()
    return reserva


def cancelar_reserva(reserva, usuario, motivo_cancelamento):
    if not reserva:
        raise RegraReservaErro("Reserva não encontrada.")

    if not usuario.is_admin and reserva.usuario_id != usuario.id:
        raise PermissionError("Você não tem permissão para cancelar esta reserva.")

    if reserva.status == "cancelada":
        raise RegraReservaErro("Esta reserva já está cancelada.")

    motivo_cancelamento = (motivo_cancelamento or "").strip()
    if not motivo_cancelamento:
        raise RegraReservaErro("Informe o motivo do cancelamento.")

    reserva.status = "cancelada"
    reserva.motivo_cancelamento = motivo_cancelamento
    reserva.cancelada_em = datetime.now()
    db.session.commit()
    return reserva


def criar_bloqueio_sala(sala_id, data_inicio_str, data_fim_str, motivo):
    sala = db.session.get(Sala, int(sala_id))
    if not sala:
        raise RegraReservaErro("Sala não encontrada.")

    data_inicio = parse_date(data_inicio_str)
    data_fim = parse_date(data_fim_str)

    if data_inicio < date.today():
        raise RegraReservaErro("Não é permitido bloquear uma sala em datas passadas.")

    if data_fim < data_inicio:
        raise RegraReservaErro("A data de término deve ser igual ou posterior à data de início.")

    bloqueios = BloqueioSala.query.filter(
        BloqueioSala.sala_id == sala.id,
        BloqueioSala.ativo.is_(True),
        BloqueioSala.data <= data_fim,
        or_(BloqueioSala.data_fim.is_(None), BloqueioSala.data_fim >= data_inicio),
    ).all()
    for bloqueio in bloqueios:
        raise RegraReservaErro("Já existe um bloqueio ativo para esta sala no período informado.")

    reservas = Reserva.query.filter(
        Reserva.sala_id == sala.id,
        Reserva.status == "ativa",
        Reserva.data >= data_inicio,
        Reserva.data <= data_fim,
    ).all()
    for reserva in reservas:
        raise RegraReservaErro(
            f"Já existe reserva ativa nesta sala em {reserva.data.strftime('%d/%m/%Y')} "
            f"das {reserva.hora_inicio.strftime('%H:%M')} às {reserva.hora_fim.strftime('%H:%M')}."
        )

    bloqueio = BloqueioSala(
        sala_id=sala.id,
        data=data_inicio,
        data_fim=data_fim,
        hora_inicio=time(hour=0),
        hora_fim=time(hour=23, minute=59),
        motivo=(motivo or "").strip() or "Manutenção",
        ativo=True,
    )
    db.session.add(bloqueio)
    db.session.commit()
    return bloqueio


def cancelar_bloqueio_sala(bloqueio):
    if not bloqueio:
        raise RegraReservaErro("Bloqueio não encontrado.")
    bloqueio.ativo = False
    db.session.commit()
    return bloqueio


def gerar_horarios_disponiveis(sala, data):
    duracao_horas = 1
    horarios = []
    inicio = datetime.combine(data, time(hour=8))
    fim_expediente = datetime.combine(data, time(hour=22))

    reservas = Reserva.query.filter_by(sala_id=sala.id, data=data, status="ativa").all()
    bloqueios = BloqueioSala.query.filter(
        BloqueioSala.sala_id == sala.id,
        BloqueioSala.ativo.is_(True),
        BloqueioSala.data <= data,
        or_(BloqueioSala.data_fim.is_(None), BloqueioSala.data_fim >= data),
    ).all()

    while inicio + timedelta(hours=duracao_horas) <= fim_expediente:
        fim = inicio + timedelta(hours=duracao_horas)
        inicio_hora = inicio.time()
        fim_hora = fim.time()
        reservas_sobrepostas = [
            reserva
            for reserva in reservas
            if horarios_sobrepostos(inicio_hora, fim_hora, reserva.hora_inicio, reserva.hora_fim)
        ]
        bloqueios_sobrepostos = [
            bloqueio
            for bloqueio in bloqueios
            if horarios_sobrepostos(inicio_hora, fim_hora, bloqueio.hora_inicio, bloqueio.hora_fim)
        ]
        ocupado = bool(reservas_sobrepostas)
        bloqueado = bool(bloqueios_sobrepostos)
        finalidade = ", ".join(reserva.finalidade for reserva in reservas_sobrepostas)
        motivo_bloqueio = ", ".join(bloqueio.motivo for bloqueio in bloqueios_sobrepostos)
        horarios.append(
            {
                "inicio": inicio_hora,
                "fim": fim_hora,
                "disponivel": sala.disponivel and not ocupado and not bloqueado,
                "status": "Bloqueado" if bloqueado else "Reservado" if ocupado else "Disponível",
                "finalidade": finalidade,
                "motivo_bloqueio": motivo_bloqueio,
            }
        )
        inicio = fim

    return horarios
