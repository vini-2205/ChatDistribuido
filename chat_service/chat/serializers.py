from rest_framework import serializers

from .models import Conversa, Mensagem, Participante

from . import mongo

class ParticipanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participante
        fields = ['usuario_id', 'username']


class MensagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mensagem
        fields = ['id', 'conversa_id', 'remetente_id', 'remetente_username', 'conteudo', 'enviada_em']


class ConversaSerializer(serializers.ModelSerializer):
    participantes = ParticipanteSerializer(many=True, read_only=True)
    ultima_mensagem = serializers.SerializerMethodField()

    class Meta:
        model = Conversa
        fields = ['id', 'tipo', 'nome', 'criado_por_id', 'criada_em', 'participantes', 'ultima_mensagem']

    def get_ultima_mensagem(self, obj):
        return mongo.ultima_mensagem(obj.id)


class NovoParticipanteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField(max_length=150)


class NovaConversaSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=Conversa.TIPOS)
    nome = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    participantes = NovoParticipanteSerializer(many=True)
