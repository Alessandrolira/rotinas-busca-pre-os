import requests 
import pandas as pd
import paramiko
from io import BytesIO

# ============================= #
#  CONFIGURAÇÃO 
# ============================= 

url = "https://kitcorretoramil.com.br/wp-admin/admin-ajax.php?action=ktc_get_price_table_values" 

payload = { 
    "pf": "false",
    "Estado": "INTERIOR SP - 1",
    "Numero_de_vidas_plano": "5 a 29",
    "Compulsorio": "MEI",
    "Linha": "Linha Amil",
    "Coparticipação": "Com coparticipação30" 
} 

headers = { 
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://kitcorretoramil.com.br",
    "Referer": "https://kitcorretoramil.com.br/linha-selecionada-pme/tabela-de-precos-pme/" 
} 

# ============================= 
# REQUEST 
# ============================= 

regiões = [
    "INTERIOR SP - 1",
    "INTERIOR SP - 2",
    "BAHIA",
    "CEARÁ",
    "DISTRITO FEDERAL",
    "GOIÁS",
    "MARANHÃO",
    "MINAS GERAIS",
    "PARAÍBA",
    "PARANÁ",
    "PERNAMBUCO",
    "RIO DE JANEIRO",
    "RIO GRANDE DO SUL",
    "RIO GRANDE DO NORTE",
    "SANTA CATARINA",
    "SÃO PAULO",
]

tipo_empresa = [
    "MEI",
    "Demais Empresas",
    "Livre Adesão",
    "Compulsório"
]

linhas = [
    "Linha Selecionada",
    "Linha Amil"
]

coparticipacao = [
    "Com Coparticipação30",
    "Com Coparticipação40",
    "Com Coparticipação parcial"
]

resposta = []

for copart in coparticipacao:
    payload["Coparticipação"] = copart
    for linha in linhas:
        payload["Linha"] = linha
        for regiao in regiões:                                                                                                                                                                                                                                                                                                                                                                           
            for empresa in tipo_empresa:
                payload["Compulsorio"] = empresa
                payload["Estado"] = regiao
                response = requests.post( url, json=payload, # 🔥 ISSO É O PONTO-CHAVE
                                    headers=headers 
                                ) 

                data = response.json()
                print(response.status_code, regiao, empresa, linha, len(data), copart)
                resposta.append({f"{regiao}_{empresa}_{copart}": data})

# ============================= 
# VALIDAÇÃO 
# ============================= 

if not isinstance(data, dict): 
    raise Exception(f"❌ Resposta inesperada: {data}") 

# ============================= 
# NORMALIZAÇÃO 
# ============================= 

faixas = [
    "0-18",
    "19-23",
    "24-28",
    "29-33",
    "34-38",
    "39-43",
    "44-48",
    "49-53",
    "54-58",
    "59+"
]

linhas = []

for bloco in resposta:
    for chave_bloco, planos in bloco.items():

        regiao, tipo_empresa, copart = chave_bloco.rsplit("_", 2)

        for chave_plano, valores in planos.items():

            # =============================
            # FILTRO LA / CO 🔥
            # =============================
            chave_lower = chave_plano.lower()

            if tipo_empresa == "Demais Empresas" and "_la_" in chave_lower:
                continue

            if not isinstance(valores, list) or len(valores) < 12:
                continue

            plano = valores[0]
            acomodacao = valores[1]
            precos = valores[2:12]
            vidas = valores[-1]  # ex: "5 a 29" ou "30 a 99"

            # =============================
            # REGRA DE NEGÓCIO 🔥
            # =============================
            if vidas == "30 a 99":
                if tipo_empresa not in ["Compulsório", "Livre Adesão"]:
                    continue
            else:
                if tipo_empresa not in ["MEI", "Demais Empresas"]:
                    continue
            # =============================

            for faixa, preco in zip(faixas, precos):
                linhas.append({
                    "Plano": plano,
                    "Acomodação": acomodacao,
                    "Região": regiao,
                    "Faixa Etaria": faixa,
                    "Tipo_Empresa": tipo_empresa,
                    "Preço": float(preco.replace(".", "").replace(",", ".")),
                    "Vidas": vidas,
                    "Coparticipação": copart
                })


        
df = pd.DataFrame(linhas) 
print(df.head()) 
       
# ============================= 
# EXPORTAÇÃO 
# ============================= 

HOST_SFTP="192.168.9.4"
PORT_SFTP=2022
USER_ADMIN_SFTP="AppAdmin"
PASSWORD_ADMIN_SFTP="PQZ@187wbazx"
REMOTE_DIR = "/Atendimentoaocorretor-GoTolky/configuracao/arquivos_base"
REMOTE_FILE = "Valores-amil.xlsx"

# ============================
# GERA O EXCEL EM MEMÓRIA
# ============================
buffer = BytesIO()
df.to_excel(buffer, index=False, engine="openpyxl")
buffer.seek(0)

# ============================
# CONECTA NO SFTP
# ============================
transport = paramiko.Transport((HOST_SFTP, PORT_SFTP))
transport.connect(username=USER_ADMIN_SFTP, password=PASSWORD_ADMIN_SFTP)

sftp = paramiko.SFTPClient.from_transport(transport)

# ============================
# GARANTE QUE A PASTA EXISTE
# ============================
def ensure_remote_dir(sftp, path):
    dirs = path.strip("/").split("/")
    current = ""
    for d in dirs:
        current += f"/{d}"
        try:
            sftp.chdir(current)
        except:
            sftp.mkdir(current)

ensure_remote_dir(sftp, REMOTE_DIR)

# ============================
# ENVIA O ARQUIVO
# ============================
remote_path = f"{REMOTE_DIR}/{REMOTE_FILE}"

with sftp.open(remote_path, "wb") as f:
    f.write(buffer.read())


# ============================
# FECHA
# ============================
sftp.close()
transport.close()

print(f"✅ Excel enviado com sucesso para:\n{remote_path}")

# df.to_excel("Valores-amil.xlsx", index=False) 
# print("\n✅ Excel gerado com sucesso: Valores-amil.xlsx")