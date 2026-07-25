# Ficheiro: main.py
# Ponto de entrada do projeto. Roda automaticamente ao ligar o ESP32.
#
# Ordem de execucao a cada boot:
#   1) Wi-Fi via GerenciadorWifi -- conecta na rede salva, ou abre o portal
#      de configuracao (AP "ESP_Config_Setup") se nao conseguir. A fita
#      mostra um "radar" azul procurando rede, e "respira" em ambar
#      enquanto espera ser configurada pelo portal.
#   2) Atualizacao via OTAUpdater -- confere a versao no GitHub e baixa
#      main.py/index.html se houver algo novo. A fita mostra um "meteoro"
#      azul baixando, pulsa verde no sucesso (e reinicia sozinho) ou
#      pulsa vermelho se falhar.
#   3) Servidor HTTP (serve o index.html e o /api/led) junto com o loop
#      de animacoes da fita, tudo rodando via asyncio.

import gc
import json

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

from led_fx import ControladorLED
from wifi_manager import GerenciadorWifi
from ota_updater import OTAUpdater
from config import URL_VERSAO, ARQUIVOS_REMOTOS

PORTA = 80
ARQUIVO_HTML = 'index.html'

controlador = ControladorLED()
HTML_CACHE = b''


def _decodificar_valor(valor):
    valor = valor.replace('+', ' ')
    if '%' not in valor:
        return valor
    partes = valor.split('%')
    resultado = partes[0]
    for parte in partes[1:]:
        if len(parte) >= 2:
            try:
                resultado += chr(int(parte[:2], 16)) + parte[2:]
                continue
            except ValueError:
                pass
        resultado += '%' + parte
    return resultado


def analisar_parametros(caminho):
    parametros = {}
    if '?' not in caminho:
        return parametros
    query = caminho.split('?', 1)[1]
    for par in query.split('&'):
        if '=' not in par:
            continue
        chave, valor = par.split('=', 1)
        parametros[chave] = _decodificar_valor(valor)
    return parametros


async def atender_cliente(reader, writer):
    try:
        linha_requisicao = await reader.readline()
        if not linha_requisicao:
            return
        # Descarta o resto dos cabeçalhos HTTP, não precisamos deles aqui
        while True:
            linha = await reader.readline()
            if linha in (b'\r\n', b''):
                break

        partes = linha_requisicao.decode().split(' ')
        if len(partes) < 2:
            return
        caminho = partes[1]

        if caminho.startswith('/api/led'):
            params = analisar_parametros(caminho)
            try:
                controlador.processar_comandos(
                    efeito=params.get('fx', 'fixa'),
                    r=int(params.get('r', 0)),
                    g=int(params.get('g', 255)),
                    b=int(params.get('b', 200)),
                    brilho=int(params.get('brilho', 150)),
                    qtd=int(params.get('qtd', controlador.num_leds)),
                    vel=int(params.get('vel', 50)),
                    total_leds=int(params.get('total', controlador.num_leds)),
                )
                writer.write(
                    b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n'
                    b'Access-Control-Allow-Origin: *\r\nConnection: close\r\n\r\nOK'
                )
            except (ValueError, TypeError) as erro:
                print('Parametros invalidos em /api/led:', erro)
                writer.write(b'HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\nParametros invalidos')

        elif caminho.startswith('/api/estado'):
            r, g, b = controlador.cor_atual
            estado = json.dumps({
                'fx': controlador.efeito_atual,
                'r': r, 'g': g, 'b': b,
                'brilho': controlador.brilho,
                'qtd': controlador.qtd_acesos,
                'vel': controlador.velocidade,
                'total': controlador.num_leds,
            })
            writer.write(
                b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n'
                b'Access-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n'
            )
            writer.write(estado.encode())

        elif caminho in ('/', '/index.html'):
            writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n')
            writer.write(HTML_CACHE)

        else:
            writer.write(b'HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\nNao encontrado')

        await writer.drain()

    except Exception as erro:
        print('Erro ao atender cliente:', erro)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        gc.collect()


async def loop_animacoes():
    while True:
        controlador.atualizar_animacoes()
        await asyncio.sleep_ms(5)


async def principal():
    global HTML_CACHE

    # Guarda o preset que o ControladorLED acabou de carregar do disco
    # (no __init__), antes que o wifi/OTA usem a fita pros proprios
    # efeitos de status abaixo.
    preset = {
        'efeito': controlador.efeito_atual,
        'cor': controlador.cor_atual,
        'brilho': controlador.brilho,
        'qtd': controlador.qtd_acesos,
        'vel': controlador.velocidade,
    }

    # 1) Wi-Fi -- conecta ou abre o portal de configuracao (AP).
    #    Fica bloqueado aqui ate ter uma rede de verdade funcionando.
    gerenciador_wifi = GerenciadorWifi(controlador)
    ip = gerenciador_wifi.conectar()
    print('Wi-Fi conectado! Acesse: http://%s/' % ip)

    # 2) OTA -- confere versao no GitHub. Se atualizar, reinicia sozinho
    #    e este ponto do codigo nunca eh alcançado nesta execucao.
    atualizador = OTAUpdater(controlador, URL_VERSAO, ARQUIVOS_REMOTOS)
    atualizador.checar_e_atualizar()

    # 3) Servidor HTTP + loop de animacoes
    with open(ARQUIVO_HTML, 'r') as f:
        HTML_CACHE = f.read().encode()

    gc.collect()

    await asyncio.start_server(atender_cliente, '0.0.0.0', PORTA)
    print('Servidor no ar na porta %d' % PORTA)

    # Restaura o preset salvo (o wifi/OTA usaram a fita para os proprios
    # efeitos de status enquanto rodavam). fixa/desligar nao sao
    # redesenhados sozinhos pelo loop de animacoes, entao forca um
    # redesenho manual pra fita realmente refletir o preset restaurado.
    controlador.efeito_atual = preset['efeito']
    controlador.cor_atual = preset['cor']
    controlador.brilho = preset['brilho']
    controlador.qtd_acesos = preset['qtd']
    controlador.velocidade = preset['vel']
    controlador.redesenhar_estado_atual()

    asyncio.create_task(loop_animacoes())

    while True:
        await asyncio.sleep(3600)


try:
    asyncio.run(principal())
except KeyboardInterrupt:
    print('Encerrado manualmente.')
finally:
    asyncio.new_event_loop()
