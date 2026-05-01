import network
import socket
import time
import machine
import json
from machine import Pin
from neopixel import NeoPixel

# --- Hardware ---
led_interno = Pin(8, Pin.OUT)       # LED azul da placa ESP32-C3
num_leds = 21
fita = NeoPixel(Pin(1), num_leds)   # Fita RGB no Pino 1

# ==========================================
# ⚙️ GERENCIADOR DE WI-FI INTELIGENTE (OTA & AP)
# ==========================================
def conectar_ou_configurar():
    # 1. Tenta ler as credenciais salvas na memória da placa
    try:
        with open("wifi.json", "r") as f:
            cred = json.loads(f.read())
            ssid_salvo = cred.get("ssid", "")
            senha_salva = cred.get("senha", "")
    except:
        ssid_salvo = ""
        senha_salva = ""

    # 2. Prepara o modo "Cliente"
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    if ssid_salvo:
        print(f"🔄 Tentando conectar na rede salva: {ssid_salvo}...")
        sta.connect(ssid_salvo, senha_salva)
        
        tentativas = 0
        while not sta.isconnected() and tentativas < 20: 
            led_interno.value(not led_interno.value()) # Pisca o LED enquanto tenta
            time.sleep(0.5)
            tentativas += 1

        if sta.isconnected():
            ip = sta.ifconfig()[0]
            print(f"✅ Conectado com sucesso! IP: {ip}")
            led_interno.value(1) # Acende fixo para confirmar
            return ip

    # 3. Falhou ou sem rede? Vira Roteador (Access Point)
    led_interno.value(0)
    print("❌ Falha ao conectar. Entrando em Modo Access Point (Configuração)...")
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP_Config") # Nome da rede no celular
    print("📡 Conecte-se na rede Wi-Fi 'ESP_Config' com seu celular.")
    print("🌐 Depois, abra o navegador e acesse: http://192.168.4.1")

    # 4. Cria servidor web temporário para hospedar a página
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(1)

    while True:
        # Pisca rápido indicando modo AP de Configuração
        led_interno.value(not led_interno.value()) 
        try:
            s.settimeout(0.2) # Timeout para permitir o pisca do LED
            conn, addr = s.accept()
            req = conn.recv(1024).decode('utf-8')

            # Captura a senha enviada pelo celular
            if '/salvar?ssid=' in req:
                try:
                    url_part = req.split(' ')[1]
                    params = url_part.split('?')[1].split('&')
                    novo_ssid = params[0].split('=')[1].replace('%20', ' ')
                    nova_senha = params[1].split('=')[1].replace('%20', ' ')

                    with open("wifi.json", "w") as f:
                        f.write(json.dumps({"ssid": novo_ssid, "senha": nova_senha}))

                    conn.send("HTTP/1.1 200 OK\n\n✅ Credenciais salvas! Reiniciando a placa...")
                    conn.close()
                    time.sleep(2)
                    machine.reset() # ♻️ Reinicia a placa para aplicar
                except:
                    pass

            # A Página Verde e Preta Hacker - Layout Profissional
            html = """<!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Setup Cassino ESP32</title>
                <style>
                    body {
                        background-color: #0d0d0d;
                        color: #00ff00;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        background: #151515;
                        padding: 40px 30px;
                        border-radius: 12px;
                        box-shadow: 0 0 20px rgba(0, 255, 0, 0.15);
                        width: 100%;
                        max-width: 320px;
                        text-align: center;
                        border: 1px solid #222;
                        transition: box-shadow 0.3s ease;
                    }
                    .container:hover {
                        box-shadow: 0 0 30px rgba(0, 255, 0, 0.3);
                        border-color: #00ff00;
                    }
                    h2 {
                        margin-top: 0;
                        font-size: 24px;
                        font-weight: 600;
                        letter-spacing: 1px;
                        text-transform: uppercase;
                    }
                    p {
                        font-size: 13px;
                        color: #888;
                        margin-bottom: 25px;
                        line-height: 1.4;
                    }
                    input[type="text"], input[type="password"] {
                        width: 100%;
                        padding: 14px;
                        margin-bottom: 15px;
                        border: 1px solid #333;
                        border-radius: 8px;
                        background: #000;
                        color: #00ff00;
                        font-size: 14px;
                        box-sizing: border-box;
                        transition: all 0.3s;
                    }
                    input[type="text"]:focus, input[type="password"]:focus {
                        outline: none;
                        border-color: #00ff00;
                        box-shadow: 0 0 10px rgba(0, 255, 0, 0.4);
                        background: #050505;
                    }
                    input[type="text"]::placeholder, input[type="password"]::placeholder {
                        color: #555;
                    }
                    input[type="submit"] {
                        width: 100%;
                        padding: 15px;
                        background-color: #00aa00;
                        color: #000;
                        border: none;
                        border-radius: 8px;
                        font-size: 16px;
                        font-weight: 800;
                        cursor: pointer;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        transition: background 0.3s, transform 0.1s;
                        margin-top: 10px;
                    }
                    input[type="submit"]:hover {
                        background-color: #00ff00;
                    }
                    input[type="submit"]:active {
                        transform: scale(0.97);
                    }
                    .icon {
                        font-size: 48px;
                        margin-bottom: 10px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon">🎰</div>
                    <h2>Setup Cassino</h2>
                    <p>Conecte o sistema à sua rede Wi-Fi local para ativar a comunicação.</p>
                    <form action="/salvar" method="GET">
                        <input type="text" name="ssid" placeholder="Nome da Rede (SSID)" required>
                        <input type="password" name="senha" placeholder="Senha (vazio se aberta)">
                        <input type="submit" value="Conectar ⚡">
                    </form>
                </div>
            </body>
            </html>"""

            conn.send("HTTP/1.1 200 OK\nContent-Type: text/html\n\n" + html)
            conn.close()
        except OSError:
            pass # Apenas o timeout estourando para continuar piscando o LED

# --- Efeitos Visuais de Fita LED ---
def limpar():
    for i in range(num_leds): fita[i] = (0, 0, 0)
    fita.write()

def wheel(pos):
    if pos < 85: return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

def efeito_resultado(cor, vezes=5):
    for _ in range(vezes):
        for i in range(num_leds): fita[i] = cor
        fita.write()
        time.sleep(0.1)
        limpar()
        time.sleep(0.1)

# --- INÍCIO DO SISTEMA ---
IP_DA_PLACA = conectar_ou_configurar()
limpar()

# OTA: Liga o WebREPL se você já o configurou via terminal antes
try:
    import webrepl
    webrepl.start()
    print("🌐 WebREPL (OTA) Ativado!")
except:
    print("⚠️ WebREPL não configurado. Tudo bem, OTA desligado por enquanto.")

# O Servidor que ouve o PC
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(1)
s.settimeout(0.05) # Escuta hiper-rápida para não congelar o Arco-íris!

print(f"🚀 Servidor do Cassino rodando no IP: {IP_DA_PLACA}")

estado_atual = "parado"
arco_iris_j = 0

while True:
    try:
        # Tenta escutar o comando do PC
        conn, addr = s.accept()
        request = conn.recv(1024).decode()
        conn.send('HTTP/1.1 200 OK\n\n')
        conn.close()
        
        # Executa as Ações
        if "/intro" in request:
            print("🎰 [LOG] ABERTURA -> Arco-íris ativado")
            estado_atual = "intro"
        elif "/parar" in request:
            print("🛑 [LOG] Aposta feita! Parando LEDs.")
            estado_atual = "parado"
            limpar()
        elif "/loading" in request:
            print("⏳ [LOG] Sorteando (Loading Azul)...")
            estado_atual = "parado"
            limpar()
            for i in range(num_leds): 
                fita[i] = (0, 0, 255); fita.write(); time.sleep(0.05)
            limpar()
        elif "/ganhou" in request:
            print("🎉 [LOG] RESULTADO: Vitória (Verde)")
            estado_atual = "parado"
            efeito_resultado((0, 255, 0))
        elif "/perdeu" in request:
            print("💸 [LOG] RESULTADO: Derrota (Vermelho)")
            estado_atual = "parado"
            efeito_resultado((255, 0, 0))
        elif "/empate" in request:
            print("😐 [LOG] RESULTADO: Empate (Amarelo)")
            estado_atual = "parado"
            efeito_resultado((255, 255, 0))
        elif "/exit" in request:
            print("💰 [LOG] Jogador sacou a grana (Loading Verde)")
            estado_atual = "parado"
            for i in range(num_leds): 
                fita[i] = (0, 255, 0); fita.write(); time.sleep(0.02)
            limpar()
            
    except OSError:
        # Nenhum comando do PC chegou, pode desenhar os LEDs!
        pass
        
    # Animação de fundo (Multitarefa na prática)
    if estado_atual == "intro":
        for i in range(num_leds):
            fita[i] = wheel((i * 256 // num_leds + arco_iris_j) & 255)
        fita.write()
        arco_iris_j = (arco_iris_j + 5) % 256
        time.sleep(0.01)
