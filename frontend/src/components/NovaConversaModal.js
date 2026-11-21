import React, { useEffect, useState } from 'react';
import api, { mensagemErro } from '../services/api';
import './NovaConversaModal.css';

// Busca usuários no Serviço de Autenticação e cria a conversa no Serviço de Chat
const NovaConversaModal = ({ onFechar, onCriada }) => {
  const [tipo, setTipo] = useState('PRIVADA');
  const [nomeGrupo, setNomeGrupo] = useState('');
  const [busca, setBusca] = useState('');
  const [usuarios, setUsuarios] = useState([]);
  const [selecionados, setSelecionados] = useState([]);
  const [erro, setErro] = useState('');
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      api.get('/auth/usuarios/', { params: busca ? { busca } : {} })
        .then(({ data }) => setUsuarios(data))
        .catch(() => setUsuarios([]));
    }, 250);
    return () => clearTimeout(t);
  }, [busca]);

  const alternar = (u) => {
    if (tipo === 'PRIVADA') {
      setSelecionados([u]);
      return;
    }
    setSelecionados((prev) => (prev.some((s) => s.id === u.id) ? prev.filter((s) => s.id !== u.id) : [...prev, u]));
  };

  const criar = async (e) => {
    e.preventDefault();
    setErro('');
    setSalvando(true);
    try {
      const { data } = await api.post('/chat/conversas/', {
        tipo,
        nome: tipo === 'GRUPO' ? nomeGrupo : '',
        participantes: selecionados.map(({ id, username }) => ({ id, username })),
      });
      onCriada(data);
    } catch (error) {
      setErro(mensagemErro(error));
      setSalvando(false);
    }
  };

  const valido = selecionados.length > 0 && (tipo === 'PRIVADA' || nomeGrupo.trim());

  return (
    <div className="modal-fundo" onClick={onFechar}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={criar}>
        <h2>Nova conversa</h2>
        <div className="abas">
          {['PRIVADA', 'GRUPO'].map((t) => (
            <button type="button" key={t} className={tipo === t ? 'ativa' : ''}
                    onClick={() => { setTipo(t); setSelecionados([]); }}>
              {t === 'PRIVADA' ? 'Privada (1:1)' : 'Grupo (1:N)'}
            </button>
          ))}
        </div>
        {tipo === 'GRUPO' && (
          <input className="campo" placeholder="Nome do grupo" value={nomeGrupo}
                 onChange={(e) => setNomeGrupo(e.target.value)} />
        )}
        <input className="campo" placeholder="Buscar usuário" value={busca} onChange={(e) => setBusca(e.target.value)} />
        <ul className="lista-usuarios">
          {usuarios.length === 0 && <li className="vazio">Nenhum usuário encontrado.</li>}
          {usuarios.map((u) => (
            <li key={u.id}>
              <label>
                <input type={tipo === 'PRIVADA' ? 'radio' : 'checkbox'} name="usuario"
                       checked={selecionados.some((s) => s.id === u.id)} onChange={() => alternar(u)} />
                <span>{u.nome}</span>
                {u.nome !== u.username && <span className="login">@{u.username}</span>}
              </label>
            </li>
          ))}
        </ul>
        {erro && <span className="erro">{erro}</span>}
        <div className="acoes">
          <button type="button" className="botao secundario" onClick={onFechar}>Cancelar</button>
          <button type="submit" className="botao" disabled={!valido || salvando}>Criar</button>
        </div>
      </form>
    </div>
  );
};

export default NovaConversaModal;
