import os
import time
import subprocess
from google import genai
from google.genai import types
from google.genai.errors import ServerError

# Inicializa o cliente do Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ==========================================
# 1. FERRAMENTAS ATÓMICAS E SEGURAS (WHITELIST)
# ==========================================

def check_network_status() -> str:
    """Inspeciona o estado das interfaces de rede e a tabela de rotas do roteador simulado."""
    print("\n[AGENTE - SEGURO] A verificar o estado das interfaces e rotas...")
    try:
        cmd_link = "docker exec net_router ip link show"
        cmd_route = "docker exec net_router ip route show"
        
        res_link = subprocess.run(cmd_link, shell=True, capture_output=True, text=True, timeout=10)
        res_route = subprocess.run(cmd_route, shell=True, capture_output=True, text=True, timeout=10)
        
        output = f"--- INTERFACES DE REDE ---\n{res_link.stdout}\n--- TABELA DE ROTAS ---\n{res_route.stdout}"
        print(f"[RESULTADO OBTIDO]:\n{output}")
        return output
    except Exception as e:
        return f"Erro ao inspecionar a rede: {str(e)}"

def restore_interface(interface_name: str) -> str:
    """Ativa uma interface de rede específica (ex: eth1). Apenas nomes predefinidos são permitidos por segurança."""
    # Whitelist rígida: o agente NUNCA poderá executar comandos fora desta lista
    allowed_interfaces = ["eth0", "eth1"]
    
    if interface_name not in allowed_interfaces:
        return f"Erro de segurança: A interface '{interface_name}' não é permitida ou não existe na política de segurança."
    
    print(f"\n[AGENTE - SEGURO] A executar restauração autorizada na interface: {interface_name}")
    try:
        cmd = f"docker exec net_router ip link set {interface_name} up"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            msg = f"Sucesso: A interface {interface_name} foi reativada com êxito."
            print(f"[+] {msg}")
            return msg
        else:
            err_msg = f"Erro ao reativar interface: {result.stderr or result.stdout}"
            print(f"[-] {err_msg}")
            return err_msg
    except Exception as e:
        return f"Erro crítico ao executar comando de restauração: {str(e)}"

# Mapeamento seguro das funções permitidas
tools_map = {
    "check_network_status": check_network_status,
    "restore_interface": restore_interface
}

def send_message_with_retry(chat, message, max_retries=3, delay=5):
    """Envia mensagem ao Gemini com retentativa automática em caso de erro 503."""
    for attempt in range(max_retries):
        try:
            return chat.send_message(message)
        except ServerError as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                print(f"\n[!] Servidor ocupado (503). A aguardar {delay}s antes de tentar novamente (Tentativa {attempt + 1}/{max_retries})...")
                time.sleep(delay)
            else:
                raise e
    raise Exception("Servidor do Gemini indisponível após várias tentativas.")

def run_monitoring_cycle():
    """Executa um ciclo único de inspeção e remediação utilizando apenas ferramentas seguras."""
    print("\n" + "="*60)
    print(f"[*] A iniciar ciclo de monitorização segura: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Passamos as funções Python diretas no array de tools
    chat = client.chats.create(
        model="gemini-3.5-flash-lite",
        config=types.GenerateContentConfig(
            tools=[check_network_status, restore_interface],
            temperature=0.1
        )
    )

    prompt_monitorizacao = (
        "Faça uma verificação proativa da rede utilizando exclusivamente as ferramentas disponíveis. "
        "Inspecione o estado das interfaces e rotas. "
        "Se identificar alguma interface caída ou anomalia, utilize a ferramenta de restauração apropriada para reativá-la. "
        "Caso esteja tudo operacional, relate que a rede está saudável."
    )

    response = send_message_with_retry(chat, prompt_monitorizacao)

    while True:
        if response.function_calls:
            for function_call in response.function_calls:
                fn_name = function_call.name
                fn_args = function_call.args
                
                if fn_name in tools_map:
                    # Executa a função restrita correspondente de forma segura
                    tool_result = tools_map[fn_name](**fn_args)
                    response = send_message_with_retry(
                        chat,
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": tool_result}
                        )
                    )
                else:
                    print(f"[-] Tentativa de chamada a ferramenta desconhecida bloqueada: {fn_name}")
        else:
            print("\n[RELATÓRIO DO AGENTE NESTE CICLO]:\n" + response.text)
            break

if __name__ == "__main__":
    CHECK_INTERVAL_SECONDS = 20 
    
    print("==================================================")
    print("  AGENTE FCAPS AUTÓNOMO - MODO SEGURO (WHITELIST)")
    print(f"  Intervalo de verificação: {CHECK_INTERVAL_SECONDS} segundos")
    print("==================================================")
    
    try:
        while True:
            run_monitoring_cycle()
            print(f"\n[*] Ciclo concluído. A aguardar {CHECK_INTERVAL_SECONDS} segundos para a próxima verificação...")
            time.sleep(CHECK_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\n[!] Monitorização interrompida pelo utilizador. Encerrando agente...")