import { nomeConversa } from './pages/Chat';

test('conversa privada exibe o nome do outro participante', () => {
  const conversa = {
    tipo: 'PRIVADA',
    participantes: [{ usuario_id: 1, username: 'ana' }, { usuario_id: 2, username: 'bruno' }],
  };
  expect(nomeConversa(conversa, 1)).toBe('bruno');
});

test('grupo exibe o nome do grupo', () => {
  expect(nomeConversa({ tipo: 'GRUPO', nome: 'SD', participantes: [] }, 1)).toBe('SD');
});
