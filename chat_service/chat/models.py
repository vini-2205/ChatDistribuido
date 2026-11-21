from django.db import models


class Conversa(models.Model):
    """Conversa privada (1:1) ou grupo (1:N)."""

    PRIVADA = 'PRIVADA'
    GRUPO = 'GRUPO'
    TIPOS = [(PRIVADA, 'Privada'), (GRUPO, 'Grupo')]

    tipo = models.CharField(max_length=10, choices=TIPOS)
    nome = models.CharField(max_length=120, blank=True)
    criado_por_id = models.BigIntegerField()
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome or f'Conversa {self.pk}'


class Participante(models.Model):
    """Usuário (do Serviço de Autenticação) que participa de uma conversa.

    O username é guardado aqui para exibição, evitando consultar o outro serviço.
    """

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name='participantes')
    usuario_id = models.BigIntegerField(db_index=True)
    username = models.CharField(max_length=150)
    entrou_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['conversa', 'usuario_id'], name='participante_unico'),
        ]


class Mensagem(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name='mensagens')
    remetente_id = models.BigIntegerField()
    remetente_username = models.CharField(max_length=150)
    conteudo = models.TextField()
    enviada_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['enviada_em', 'id']
        indexes = [models.Index(fields=['conversa', 'enviada_em'])]
