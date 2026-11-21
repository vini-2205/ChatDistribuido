"""
Regras de negócio do chat, usadas tanto pela API REST quanto pelo WebSocket.
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Count, Q

from .models import Conversa, Mensagem, Participante

TAMANHO_MAXIMO_MENSAGEM = 4000


class ErroChat(Exception):
    pass


def grupo_usuario(usuario_id):
    """Grupo do Channels de um usuário: cada conexão WebSocket dele entra nesse grupo."""
    return f'usuario_{usuario_id}'


def conversas_do_usuario(usuario_id):
    return Conversa.objects.filter(participantes__usuario_id=usuario_id).distinct()


def obter_conversa(conversa_id, usuario_id):
    conversa = conversas_do_usuario(usuario_id).filter(pk=conversa_id).first()
    if conversa is None:
        raise ErroChat('Conversa não encontrada.')
    return conversa


@transaction.atomic
def criar_conversa(criador, tipo, participantes, nome=''):
    """
    criador: dict {id, username}; participantes: lista de dicts {id, username} (sem o criador).
    Conversa privada já existente entre os dois usuários é reaproveitada.
    """
    outros = {int(p['id']): p['username'] for p in participantes if int(p['id']) != int(criador['id'])}
    if not outros:
        raise ErroChat('Informe ao menos um participante.')

    if tipo == Conversa.PRIVADA:
        if len(outros) != 1:
            raise ErroChat('Conversa privada deve ter exatamente um outro participante.')
        outro_id = next(iter(outros))
        existente = (
            Conversa.objects.filter(tipo=Conversa.PRIVADA)
            .annotate(
                total=Count('participantes', distinct=True),
                alvo=Count('participantes', filter=Q(participantes__usuario_id__in=[criador['id'], outro_id]),
                           distinct=True),
            )
            .filter(total=2, alvo=2)
            .first()
        )
        if existente:
            return existente, False
    elif tipo == Conversa.GRUPO:
        if not nome.strip():
            raise ErroChat('Grupo precisa de um nome.')
    else:
        raise ErroChat('Tipo de conversa inválido.')

    conversa = Conversa.objects.create(tipo=tipo, nome=nome.strip(), criado_por_id=criador['id'])
    membros = {int(criador['id']): criador['username'], **outros}
    Participante.objects.bulk_create(
        [Participante(conversa=conversa, usuario_id=uid, username=nome_u) for uid, nome_u in membros.items()]
    )
    return conversa, True


def salvar_mensagem(conversa_id, remetente, conteudo):
    conteudo = (conteudo or '').strip()
    if not conteudo:
        raise ErroChat('Mensagem vazia.')
    if len(conteudo) > TAMANHO_MAXIMO_MENSAGEM:
        raise ErroChat('Mensagem muito longa.')
    conversa = obter_conversa(conversa_id, remetente['id'])
    mensagem = Mensagem.objects.create(
        conversa=conversa,
        remetente_id=remetente['id'],
        remetente_username=remetente['username'],
        conteudo=conteudo,
    )
    destinatarios = list(conversa.participantes.values_list('usuario_id', flat=True))
    return mensagem, destinatarios


def mensagem_para_dict(m):
    return {
        'id': m.id,
        'conversa_id': m.conversa_id,
        'remetente_id': m.remetente_id,
        'remetente_username': m.remetente_username,
        'conteudo': m.conteudo,
        'enviada_em': m.enviada_em.isoformat(),
    }


async def publicar_async(usuarios_ids, evento):
    camada = get_channel_layer()
    for uid in usuarios_ids:
        await camada.group_send(grupo_usuario(uid), {'type': 'chat.evento', 'evento': evento})


def publicar(usuarios_ids, evento):
    """Envia um evento a todas as conexões (em qualquer réplica) dos usuários informados."""
    async_to_sync(publicar_async)(usuarios_ids, evento)
