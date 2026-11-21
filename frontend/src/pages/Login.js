import React, { useContext, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import api, { mensagemErro } from '../services/api';
import './Login.css';

const Login = () => {
  const { user, login, sessionExpired } = useContext(AuthContext);
  const navigate = useNavigate();
  const [modoCadastro, setModoCadastro] = useState(false);
  const [form, setForm] = useState({ username: '', password: '', first_name: '' });
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [enviando, setEnviando] = useState(false);

  if (user) return <Navigate to="/" />;

  const alterar = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const enviar = async (e) => {
    e.preventDefault();
    setErro('');
    setSucesso('');
    setEnviando(true);
    if (modoCadastro) {
      try {
        await api.post('/auth/registrar/', form);
        setSucesso('Conta criada. Entre com seu usuário e senha.');
        setModoCadastro(false);
      } catch (error) {
        setErro(mensagemErro(error, 'Não foi possível criar a conta.'));
      }
    } else {
      const r = await login(form.username, form.password);
      if (r.success) navigate('/');
      else setErro(r.message);
    }
    setEnviando(false);
  };

  return (
    <div className="login-pagina">
      <div className="login-cartao">
        <h1>Chat Distribuído</h1>
        <p className="subtitulo">{modoCadastro ? 'Crie sua conta' : 'Entre para conversar'}</p>
        <form onSubmit={enviar}>
          {sessionExpired && !modoCadastro && <p className="aviso">Sua sessão expirou. Entre novamente.</p>}
          {sucesso && <p className="sucesso">{sucesso}</p>}
          <input className="campo" name="username" placeholder="Usuário" autoComplete="username"
                 value={form.username} onChange={alterar} required />
          {modoCadastro && (
            <input className="campo" name="first_name" placeholder="Nome (opcional)"
                   value={form.first_name} onChange={alterar} />
          )}
          <input className="campo" name="password" type="password" placeholder="Senha"
                 autoComplete={modoCadastro ? 'new-password' : 'current-password'}
                 value={form.password} onChange={alterar} required />
          {erro && <span className="erro">{erro}</span>}
          <button className="botao" type="submit" disabled={enviando}>
            {enviando ? 'Aguarde...' : modoCadastro ? 'Criar conta' : 'Entrar'}
          </button>
        </form>
        <div className="alternar">
          {modoCadastro ? 'Já tem conta?' : 'Ainda não tem conta?'}{' '}
          <button type="button" onClick={() => { setModoCadastro(!modoCadastro); setErro(''); }}>
            {modoCadastro ? 'Entrar' : 'Cadastre-se'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Login;
