import React, { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import ChatSocket from '../services/chatSocket';
import NovaConversaModal from '../components/NovaConversaModal';
import './Chat.css';

const STATUS_TEXTO = { conectado: 'Online', conectando: 'Conectando...', desconectado: 'Reconectando...' };

export const nomeConversa = (conversa, meuId) => {
  if (conversa.tipo === 'GRUPO') return conversa.nome;
  const outro = conversa.participantes.find((p) => p.usuario_id !== meuId);
  return outro?.username || 'Conversa';
};

const horaCurta = (iso) =>
  new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

const dataUltimaAtividade = (c) => c.ultima_mensagem?.enviada_em || c.criada_em;

const Chat = () => {
  const { user, logout } = useContext(AuthContext);
  const [conversas, setConversas] = useState([]);
  const [selecionadaId, setSelecionadaId] = useState(null);
  const [mensagens, setMensagens] = useState({}); // { conversaId: [mensagem, ...] }
  const [naoLidas, setNaoLidas] = useState({});
  const [status, setStatus] = useState('conectando');
  const [replica, setReplica] = useState('');
  const [texto, setTexto] = useState('');
  const [modalAberto, setModalAberto] = useState(false);

  const socketRef = useRef(null);
  const selecionadaRef = useRef(null);
  const fimRef = useRef(null);
  selecionadaRef.current = selecionadaId;

  const carregarConversas = useCallback(async () => {
    const { data } = await api.get('/chat/conversas/');
    setConversas(data);
  }, []);

  const carregarHistorico = useCallback(async (conversaId) => {
    const { data } = await api.get(`/chat/conversas/${conversaId}/mensagens/`);
    setMensagens((prev) => ({ ...prev, [conversaId]: data }));
  }, []);

  const adicionarConversa = useCallback((conversa) => {
    setConversas((prev) => (prev.some((c) => c.id === conversa.id) ? prev : [conversa, ...prev]));
  }, []);

  const receberMensagem = useCallback((m, tempId) => {
    setMensagens((prev) => {
      const lista = prev[m.conversa_id];
      if (!lista) return prev; // histórico ainda não carregado: virá completo pela API
      if (lista.some((x) => x.id === m.id)) return prev;
      const semPendente = tempId ? lista.filter((x) => x.temp_id !== tempId) : lista;
      return { ...prev, [m.conversa_id]: [...semPendente, m] };
    });
    setConversas((prev) => prev.map((c) => (c.id === m.conversa_id ? { ...c, ultima_mensagem: m } : c)));
    if (m.conversa_id !== selecionadaRef.current && m.remetente_id !== user.id) {
      setNaoLidas((prev) => ({ ...prev, [m.conversa_id]: (prev[m.conversa_id] || 0) + 1 }));
    }
  }, [user.id]);

  useEffect(() => {
    carregarConversas();
    const socket = new ChatSocket({
      onStatus: setStatus,
      onEvento: (evento) => {
        if (evento.tipo === 'conectado') setReplica(evento.replica);
        else if (evento.tipo === 'mensagem') receberMensagem(evento.mensagem, evento.temp_id);
        else if (evento.tipo === 'nova_conversa') adicionarConversa(evento.conversa);
      },
      // Após reconectar (possivelmente em outra réplica), sincroniza o que pode ter chegado
      onReconectado: () => {
        carregarConversas();
        if (selecionadaRef.current) carregarHistorico(selecionadaRef.current);
      },
    });
    socket.conectar();
    socketRef.current = socket;
    return () => socket.fechar();
  }, [carregarConversas, carregarHistorico, receberMensagem, adicionarConversa]);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ block: 'end' });
  }, [mensagens, selecionadaId]);

  const abrirConversa = (id) => {
    setSelecionadaId(id);
    setNaoLidas((prev) => ({ ...prev, [id]: 0 }));
    if (!mensagens[id]) carregarHistorico(id);
  };

  const enviar = async (e) => {
    e.preventDefault();
    const conteudo = texto.trim();
    if (!conteudo || !selecionadaId) return;
    setTexto('');

    const tempId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const pendente = {
      temp_id: tempId, conversa_id: selecionadaId, remetente_id: user.id,
      remetente_username: user.username, conteudo, enviada_em: new Date().toISOString(), pendente: true,
    };
    setMensagens((prev) => ({ ...prev, [selecionadaId]: [...(prev[selecionadaId] || []), pendente] }));

    const enviado = socketRef.current?.enviar({ tipo: 'mensagem', conversa_id: selecionadaId, conteudo, temp_id: tempId });
    if (!enviado) {
      // WebSocket fora do ar: envia pela API REST (o servidor também publica aos participantes)
      try {
        const { data } = await api.post(`/chat/conversas/${selecionadaId}/mensagens/`, { conteudo });
        receberMensagem(data, tempId);
      } catch {
        setMensagens((prev) => ({
          ...prev,
          [selecionadaId]: prev[selecionadaId].map((m) => (m.temp_id === tempId ? { ...m, falhou: true } : m)),
        }));
      }
    }
  };

  const conversaCriada = (conversa) => {
    adicionarConversa(conversa);
    setModalAberto(false);
    abrirConversa(conversa.id);
  };

  const ordenadas = useMemo(
    () => [...conversas].sort((a, b) => dataUltimaAtividade(b).localeCompare(dataUltimaAtividade(a))),
    [conversas]
  );
  const selecionada = conversas.find((c) => c.id === selecionadaId);
  const lista = mensagens[selecionadaId] || [];

  return (
    <div className={`chat ${selecionada ? 'com-conversa' : ''}`}>
      <aside className="chat-lateral">
        <header className="chat-lateral-topo">
          <div>
            <strong>{user.nome}</strong>
            <span className={`status status-${status}`} title={replica ? `Réplica: ${replica}` : ''}>
              {STATUS_TEXTO[status]}
            </span>
          </div>
          <button className="botao secundario" onClick={logout}>Sair</button>
        </header>
        <button className="botao nova-conversa" onClick={() => setModalAberto(true)}>+ Nova conversa</button>
        <ul className="lista-conversas">
          {ordenadas.length === 0 && <li className="vazio">Nenhuma conversa ainda.</li>}
          {ordenadas.map((c) => (
            <li key={c.id}>
              <button className={c.id === selecionadaId ? 'ativa' : ''} onClick={() => abrirConversa(c.id)}>
                <span className="avatar">{c.tipo === 'GRUPO' ? '#' : nomeConversa(c, user.id)[0]?.toUpperCase()}</span>
                <span className="resumo">
                  <span className="nome">{nomeConversa(c, user.id)}</span>
                  <span className="previa">
                    {c.ultima_mensagem
                      ? `${c.ultima_mensagem.remetente_id === user.id ? 'Você' : c.ultima_mensagem.remetente_username}: ${c.ultima_mensagem.conteudo}`
                      : c.tipo === 'GRUPO' ? `${c.participantes.length} participantes` : 'Sem mensagens'}
                  </span>
                </span>
                {naoLidas[c.id] > 0 && <span className="badge">{naoLidas[c.id]}</span>}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="chat-principal">
        {!selecionada ? (
          <div className="sem-conversa">Selecione uma conversa ou crie uma nova.</div>
        ) : (
          <>
            <header className="chat-principal-topo">
              <button className="voltar" onClick={() => setSelecionadaId(null)} aria-label="Voltar">‹</button>
              <div>
                <strong>{nomeConversa(selecionada, user.id)}</strong>
                {selecionada.tipo === 'GRUPO' && (
                  <span className="participantes">{selecionada.participantes.map((p) => p.username).join(', ')}</span>
                )}
              </div>
            </header>
            <div className="mensagens">
              {lista.map((m) => {
                const minha = m.remetente_id === user.id;
                return (
                  <div key={m.id || m.temp_id} className={`mensagem ${minha ? 'minha' : ''} ${m.pendente ? 'pendente' : ''}`}>
                    {!minha && selecionada.tipo === 'GRUPO' && <span className="autor">{m.remetente_username}</span>}
                    <span className="conteudo">{m.conteudo}</span>
                    <span className="hora">{m.falhou ? 'Falhou' : horaCurta(m.enviada_em)}</span>
                  </div>
                );
              })}
              <div ref={fimRef} />
            </div>
            <form className="compositor" onSubmit={enviar}>
              <input className="campo" placeholder="Digite uma mensagem" value={texto}
                     onChange={(e) => setTexto(e.target.value)} maxLength={4000} autoFocus />
              <button className="botao" type="submit" disabled={!texto.trim()}>Enviar</button>
            </form>
          </>
        )}
      </main>

      {modalAberto && <NovaConversaModal onFechar={() => setModalAberto(false)} onCriada={conversaCriada} />}
    </div>
  );
};

export default Chat;
