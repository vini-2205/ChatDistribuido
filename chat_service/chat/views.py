from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import servico
from .middleware import NOME_REPLICA
from .serializers import ConversaSerializer, NovaConversaSerializer

from . import mongo
from bson.errors import InvalidId

TAMANHO_PAGINA = 50


def usuario_logado(request):
    # TokenUser: id e username vêm das claims do JWT emitido pelo Serviço de Autenticação
    return {'id': int(request.user.id), 'username': request.user.username}


@api_view(['GET', 'POST'])
def conversas(request):
    """
    GET  /api/chat/conversas/ — conversas do usuário logado.
    POST /api/chat/conversas/ — cria conversa privada ou grupo.
    """
    usuario = usuario_logado(request)
    if request.method == 'GET':
        qs = servico.conversas_do_usuario(usuario['id']).prefetch_related('participantes').order_by('-criada_em')
        return Response(ConversaSerializer(qs, many=True).data)

    entrada = NovaConversaSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    try:
        conversa, criada = servico.criar_conversa(usuario, **entrada.validated_data)
    except servico.ErroChat as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    dados = ConversaSerializer(conversa).data
    if criada:
        ids = [p['usuario_id'] for p in dados['participantes']]
        servico.publicar(ids, {'tipo': 'nova_conversa', 'conversa': dados})
    return Response(dados, status=status.HTTP_201_CREATED if criada else status.HTTP_200_OK)


@api_view(["GET", "POST"])
def mensagens(request, conversa_id):
    usuario = usuario_logado(request)

    if request.method == "GET":
        try:
            conversa = servico.obter_conversa(
                conversa_id,
                usuario["id"]
            )
        except servico.ErroChat as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        antes = request.query_params.get("antes")

        try:
            pagina = mongo.buscar_mensagens(
                conversa_id=conversa.id,
                antes=antes,
                limite=TAMANHO_PAGINA
            )
        except InvalidId:
            return Response(
                {"detail": "Identificador inválido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(pagina)

    try:
        mensagem, destinatarios = servico.salvar_mensagem(
            conversa_id,
            usuario,
            request.data.get("conteudo")
        )
    except servico.ErroChat as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    dados = servico.mensagem_para_dict(mensagem)

    servico.publicar(
        destinatarios,
        {"tipo": "mensagem", "mensagem": dados}
    )

    return Response(
        dados,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def saude(request):
    return Response({'servico': 'chat', 'replica': NOME_REPLICA, 'status': 'ok'})
