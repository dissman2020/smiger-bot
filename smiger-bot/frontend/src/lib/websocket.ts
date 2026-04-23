import { ProductCard } from "./types";

type TokenHandler = (token: string) => void;
type ProductsHandler = (items: ProductCard[]) => void;
type DoneHandler = (data: { conversation_id: string; confidence: number; lead_prompt: boolean; handoff_active?: boolean }) => void;
type ErrorHandler = (error: Event | string) => void;
type CloseHandler = () => void;
type HandoffHandler = (reason: string) => void;
type AgentMessageHandler = (content: string) => void;
type SystemHandler = (content: string) => void;

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private onToken: TokenHandler;
  private onProducts: ProductsHandler;
  private onDone: DoneHandler;
  private onError: ErrorHandler;
  private onClose: CloseHandler;
  private onHandoff: HandoffHandler;
  private onAgentMessage: AgentMessageHandler;
  private onSystem: SystemHandler;
  private doneReceived = false;

  constructor(
    url: string,
    onToken: TokenHandler,
    onDone: DoneHandler,
    onError: ErrorHandler,
    onClose: CloseHandler = () => {},
    onProducts: ProductsHandler = () => {},
    onHandoff: HandoffHandler = () => {},
    onAgentMessage: AgentMessageHandler = () => {},
    onSystem: SystemHandler = () => {},
  ) {
    this.url = url;
    this.onToken = onToken;
    this.onProducts = onProducts;
    this.onDone = onDone;
    this.onError = onError;
    this.onClose = onClose;
    this.onHandoff = onHandoff;
    this.onAgentMessage = onAgentMessage;
    this.onSystem = onSystem;
  }

  private sendWhenOpen(payload: string, attempt = 0) {
    const ws = this.ws;
    if (!ws) {
      this.onError("WebSocket not initialized");
      return;
    }

    if (ws.readyState === WebSocket.OPEN) {
      ws.send(payload);
      return;
    }

    // Wait for handshake completion to avoid dropping the first user message.
    if (ws.readyState === WebSocket.CONNECTING && attempt < 100) {
      setTimeout(() => this.sendWhenOpen(payload, attempt + 1), 100);
      return;
    }

    this.onError("WebSocket send failed: socket is not open");
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => resolve();

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "token") {
            this.onToken(data.content);
          } else if (data.type === "products") {
            this.onProducts(data.items || []);
          } else if (data.type === "handoff") {
            this.onHandoff(data.reason || "purchase_intent");
          } else if (data.type === "agent_message") {
            this.onAgentMessage(data.content || "");
          } else if (data.type === "system") {
            this.onSystem(data.content || "");
          } else if (data.type === "error") {
            this.onError(data.content || "Unknown error");
          } else if (data.type === "done") {
            this.doneReceived = true;
            this.onDone(data);
          }
        } catch {
          this.onToken(event.data);
        }
      };

      this.ws.onerror = (err) => {
        this.onError(err);
        reject(err);
      };

      this.ws.onclose = () => {
        this.ws = null;
        if (!this.doneReceived) {
          this.onClose();
        }
        this.doneReceived = false;
      };
    });
  }

  send(
    message: string,
    visitorId: string,
    language: string = "en",
    extras?: {
      customer_region?: string;
      customer_country_code?: string;
      customer_phone?: string;
    }
  ) {
    const payload = JSON.stringify({ message, visitor_id: visitorId, language, ...(extras || {}) });
    this.sendWhenOpen(payload);
  }

  close() {
    this.doneReceived = true;
    this.ws?.close();
    this.ws = null;
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
