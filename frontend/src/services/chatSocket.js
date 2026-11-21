import { ACCESS_KEY, renovarToken } from "./api";

/**
 * Conexão WebSocket com o Serviço de Chat, com reconexão automática.
 *
 * Se a réplica que atende a conexão cair, o Nginx direciona a reconexão para outra
 * réplica; como os eventos passam pelo Redis, nenhuma mensagem nova é perdida e o
 * histórico é recarregado pela API REST (callback onReconectado).
 */
export default class ChatSocket {
  constructor({ onEvento, onStatus, onReconectado }) {
    this.onEvento = onEvento;
    this.onStatus = onStatus;
    this.onReconectado = onReconectado;
    this.tentativas = 0;
    this.encerrado = false;
    this.jaConectou = false;
  }

  url() {
    const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
    const token = localStorage.getItem(ACCESS_KEY);
    return `${protocolo}://${window.location.host}/ws/chat/?token=${encodeURIComponent(token || "")}`;
  }

  conectar() {
    this.onStatus?.("conectando");
    this.ws = new WebSocket(this.url());

    this.ws.onopen = () => {
      this.tentativas = 0;
      this.onStatus?.("conectado");
      if (this.jaConectou) this.onReconectado?.();
      this.jaConectou = true;
    };

    this.ws.onmessage = (e) => {
      try {
        this.onEvento?.(JSON.parse(e.data));
      } catch {
        /* evento malformado: ignora */
      }
    };

    this.ws.onclose = async (e) => {
      if (this.encerrado) return;
      this.onStatus?.("desconectado");
      // 4401: token expirado/inválido — renova antes de reconectar
      if (e.code === 4401) {
        try {
          await renovarToken();
        } catch {
          return;
        }
      }
      const espera = Math.min(1000 * 2 ** this.tentativas, 10000);
      this.tentativas += 1;
      this.timer = setTimeout(() => this.conectar(), espera);
    };
  }

  enviar(evento) {
    if (this.ws?.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify(evento));
    return true;
  }

  fechar() {
    this.encerrado = true;
    clearTimeout(this.timer);
    this.ws?.close();
  }
}
