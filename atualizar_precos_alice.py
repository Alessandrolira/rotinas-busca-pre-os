import os
import re
import pandas as pd
import pdfplumber
import paramiko
from io import BytesIO

# =============================
# CONFIG
# =============================
PDF_PRECOS_ALICE = "./alice-precos/precos-alice.pdf"

OPERADORA = "ALICE"
REGIAO = "São Paulo"

# ===== SFTP =====
HOST_SFTP = "192.168.9.4"
PORT_SFTP = 2022
USER_ADMIN_SFTP = "AppAdmin"
PASSWORD_ADMIN_SFTP = "PQZ@187wbazx"

REMOTE_DIR = "/Atendimentoaocorretor-GoTolky/configuracao/arquivos_base"
REMOTE_FILE = "precos-alice.xlsx"

COLUNAS = [
    ("Equilíbrio", "Enfermaria"),
    ("Equilíbrio", "Apartamento"),
    ("Conforto", "Apartamento"),
    ("Conforto", "Apartamento+"),
    ("Super Conforto", "Apartamento"),
    ("Exclusivo", "Apartamento"),
    ("Exclusivo", "Apartamento+"),
    ("Exclusivo", "Apartamento++"),
]

# =============================
# REGEX
# =============================
RE_FAIXA = re.compile(r'(\d{1,2}\s+a\s+\d{1,2}|59\+)')
RE_PRECO = re.compile(r'R\$\s*([\d\.]+,\d{2})')

# =============================
# TEXTO PDF
# =============================
texto = ""
with pdfplumber.open(PDF_PRECOS_ALICE) as pdf:
    for p in pdf.pages:
        texto += (p.extract_text() or "") + "\n"

texto = texto.replace("\u2028", " ").replace("\u2029", " ")

# =============================
# CONTEXTOS
# =============================
contextos = [
    {"vidas": 1, "copart": "Com coparticipação total", "tipo": "Livre adesão"},
    {"vidas": 1, "copart": "Com coparticipação terapias", "tipo": "Livre adesão"},
    {"vidas": 2, "copart": "Com coparticipação", "tipo": "Livre adesão"},
    {"vidas": 2, "copart": "Sem coparticipação", "tipo": "Livre adesão"},
    {"vidas": "3-29", "copart": "Com coparticipação", "tipo": "Livre adesão"},
    {"vidas": "3-29", "copart": "Sem coparticipação", "tipo": "Livre adesão"},
    {"vidas": "3-29", "copart": "Com coparticipação", "tipo": "Adesão Compulsória"},
    {"vidas": "3-29", "copart": "Sem coparticipação", "tipo": "Adesão Compulsória"},
]

# =============================
# EXTRAÇÕES
# =============================
faixas = RE_FAIXA.findall(texto)
faixas = list(dict.fromkeys(faixas))

precos = RE_PRECO.findall(texto)

# =============================
# BUILD
# =============================
novos_registros = []
idx_preco = 0

for ctx in contextos:
    for faixa in faixas:
        for plano, acomodacao in COLUNAS:
            if idx_preco >= len(precos):
                break

            novos_registros.append({
                "Plano": plano,
                "Acomodação": acomodacao,
                "Região": REGIAO,
                "Faixa Etaria": faixa,
                "Tipo_Empresa": ctx["tipo"],
                "Preço": float(precos[idx_preco].replace(".", "").replace(",", ".")),
                "Vidas": ctx["vidas"],
                "Coparticipação": ctx["copart"],
                "Operadora": OPERADORA
            })

            idx_preco += 1

df_final = pd.DataFrame(novos_registros)

print(f"Registros ALICE gerados: {len(df_final)}")

# =====================================================
# EXPORTA EXCEL EM MEMÓRIA
# =====================================================
buffer = BytesIO()
df_final.to_excel(buffer, index=False, engine="openpyxl")
buffer.seek(0)

# =====================================================
# ENVIO PARA O SFTP
# =====================================================
transport = paramiko.Transport((HOST_SFTP, PORT_SFTP))
transport.connect(
    username=USER_ADMIN_SFTP,
    password=PASSWORD_ADMIN_SFTP
)

sftp = paramiko.SFTPClient.from_transport(transport)

def ensure_remote_dir(sftp, path):
    current = ""
    for pasta in path.strip("/").split("/"):
        current += f"/{pasta}"
        try:
            sftp.chdir(current)
        except IOError:
            sftp.mkdir(current)

ensure_remote_dir(sftp, REMOTE_DIR)

remote_path = f"{REMOTE_DIR}/{REMOTE_FILE}"

with sftp.open(remote_path, "wb") as f:
    f.write(buffer.read())

sftp.close()
transport.close()

print(f"✅ Excel enviado com sucesso para:\n{remote_path}")
