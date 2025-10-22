from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List
from datetime import datetime
from email.message import EmailMessage
import smtplib
from fpdf import FPDF
import io
from PIL import Image
import base64
import tempfile
import os


app = FastAPI()

class Report(BaseModel):
    colaborador: str
    equipa: str
    maquina: str
    turno: str
    descricao: str
    data_inicio: datetime
    data_fim: datetime
    destinatarios: List[EmailStr]
    imagens: List[str] = []

class ReportsRequest(BaseModel):
    relatorios: List[Report]

def gerar_pdf(relatorios: List[Report]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    for i, report in enumerate(relatorios, start=1):
        pdf.add_page()
        pdf.cell(0, 10, f"Relatório {i}", ln=True, align='L')
        pdf.ln(5)

        linhas = [
            ("Colaborador", report.colaborador),
            ("Equipa", report.equipa),
            ("Máquina", report.maquina),
            ("Turno", report.turno),
            ("Descrição", report.descricao),
            ("Data Início", report.data_inicio.strftime('%d/%m/%Y %H:%M')),
            ("Data Fim", report.data_fim.strftime('%d/%m/%Y %H:%M')),
            ("Data de envio", datetime.now().strftime('%d/%m/%Y %H:%M')),
        ]

        for label, valor in linhas:
            pdf.cell(50, 10, f"{label}:", border=1)
            pdf.cell(0, 10, valor, border=1, ln=True)
        pdf.ln(5)

        if report.imagens:
            adicionar_imagens_ao_pdf(pdf, report.imagens)

    return bytes(pdf.output(dest='S'))


@app.post("/enviar-relatorio")
def enviar_relatorio(request: ReportsRequest):
    if not request.relatorios:
        raise HTTPException(status_code=400, detail="Nenhum relatório fornecido")

    pdf_bytes = gerar_pdf(request.relatorios)

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "secilrelatorio@gmail.com"
    SMTP_PASSWORD = "dqfa jzii orux zsnm" 

    destinatarios = set()
    for report in request.relatorios:
        destinatarios.update(report.destinatarios)
    destinatarios = list(destinatarios)

    msg = EmailMessage()
    msg['Subject'] = f"Relatório com {len(request.relatorios)} avaria(s) Enviado"
    msg['From'] = SMTP_USER
    msg['To'] = ', '.join(destinatarios)
    msg.set_content("Segue em anexo o(s) relatório(s) em PDF.")

    msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename='relatorios.pdf')

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar email: {e}")

    return {"status": f"{len(request.relatorios)} relatório(s) enviado(s) com sucesso."}


def adicionar_imagens_ao_pdf(pdf, imagens_base64):
    for idx, img_b64 in enumerate(imagens_base64):
        try:
            img_data = base64.b64decode(img_b64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                tmp_img.write(img_data)
                tmp_img_path = tmp_img.name

            # Nova página para a imagem
            pdf.add_page()

            # Título acima da imagem
            pdf.set_font("Arial", style='B', size=14)
            pdf.cell(0, 10, f"Anexo da Avaria {idx + 1}", ln=True, align='C')
            pdf.ln(5)

            # Inserir imagem (ajustada ao tamanho da página)
            pdf.image(tmp_img_path, x=10, y=30, w=180)

            os.remove(tmp_img_path)

        except Exception as e:
            pdf.set_font("Arial", style='', size=12)
            pdf.cell(0, 10, f"Erro ao adicionar imagem {idx + 1}: {e}", ln=True)
