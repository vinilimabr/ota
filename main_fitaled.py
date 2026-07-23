# Arquivo: main.py
import socket
import time
from led_fx import ControladorLED
from wifi_manager import GerenciadorWifi
from ota_updater import OTAUpdater

# 1. Configurações Iniciais
URL_VERSAO = "https://raw.githubusercontent.com/vinilimabr/ota/refs/heads/main/version.txt"
URL_CODIGO = "https://raw.githubusercontent.com/vinilimabr/ota/refs/heads/main/main.py"

# 2. Inicializa os Módulos (Infraestrutura)
leds = ControladorLED()
rede = GerenciadorWifi(leds)
ota = OTAUpdater(leds, URL_VERSAO, URL_CODIGO)

# 3. Processo de Boot
leds.limpar()
IP_DA_PLACA = rede.conectar()

if IP_DA_PLACA and not str(IP_DA_PLACA).startswith("192.168.4."):
    ota.checar_e_atualizar()

# 4. Portal Web (Servidor IoT)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(1)
s.settimeout(0.05) 

print(f"🚀 Portal Web rodando no IP: {IP_DA_PLACA}")

# Carrega o site HTML da memória flash para a RAM (fica muito mais rápido)
try:
    with open('index.html', 'r') as f:
        html_cache = f.read()
except OSError:
    html_cache = "<h1>Erro: Arquivo index.html nao encontrado na placa!</h1>"

ultimo_tempo = time.ticks_ms()
pisca_estado = False

# --- LOOP PRINCIPAL (O MAESTRO) ---
while True:
    # Multitarefa visual (LED da placa piscando suavemente)
    tempo_atual = time.ticks_ms()
    if time.ticks_diff(tempo_atual, ultimo_tempo) >= 1000:
        pisca_estado = not pisca_estado
        leds.set_led_interno(pisca_estado)
        ultimo_tempo = tempo_atual
    
    # Escuta do Servidor
    try:
        conn, addr = s.accept()
        conn.settimeout(0.2) 
        try:
            request = conn.recv(1024).decode('utf-8')
            
            # --- ROTA 1: O Navegador pediu para ver o site ---
            if request.startswith("GET / HTTP") or request.startswith("GET /?"):
                resposta = "HTTP/1.1 200 OK\nContent-Type: text/html\nConnection: close\n\n" + html_cache
                conn.send(resposta.encode('utf-8'))
            
            # --- ROTA 2: O Celular enviou comandos pela API ---
            elif "/api/led" in request:
                # Extrai os parâmetros invisíveis da URL
                partes = request.split(' ')[1].split('?')
                if len(partes) > 1:
                    parametros = partes[1].split('&')
                    dados = {}
                    for param in parametros:
                        chave, valor = param.split('=')
                        dados[chave] = valor
                    
                    # Identifica qual ação executar
                    efeito = dados.get('fx', 'desligar')
                    
                    if efeito == 'desligar':
                        leds.limpar()
                    elif efeito == 'fixa':
                        # Transforma os textos da URL em números inteiros
                        r = int(dados.get('r', 0))
                        g = int(dados.get('g', 0))
                        b = int(dados.get('b', 0))
                        # (A lógica de brilho e efeitos animados entrará no Passo 3)
                        leds.set_cor((r, g, b))
                    
                # Responde ao celular que deu tudo certo para não travar o navegador
                conn.send("HTTP/1.1 200 OK\nContent-Type: application/json\nConnection: close\n\n{\"status\":\"ok\"}")
                
        except Exception as e:
            pass # Ignora pacotes fragmentados
        finally:
            conn.close()
            
    except OSError:
        pass # Ninguém conectou, apenas continua o loop
