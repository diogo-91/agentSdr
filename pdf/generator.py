"""
Gerador de PDF usando fpdf2 — 100% Python puro, zero dependências de sistema.
Funciona identicamente no Windows local e em qualquer VPS Linux.
"""
from datetime import datetime
from io import BytesIO

from fpdf import FPDF, XPos, YPos

from core.config import settings
from core.logger import logger
from core.exceptions import PDFGenerationError

# Cores (R, G, B)
COR_VERMELHO = (192, 57, 43)
COR_VERMELHO_CLARO = (231, 76, 60)
COR_TEXTO = (26, 26, 46)
COR_CINZA = (136, 136, 136)
COR_CINZA_CLARO = (248, 249, 250)
COR_BORDA = (220, 220, 220)
COR_BRANCO = (255, 255, 255)
COR_OBS_FUNDO = (255, 251, 240)
COR_OBS_BORDA = (255, 224, 130)

PAGE_W = 210  # A4 mm
MARGIN = 15

# Texto fixo dos termos
DADOS_BANCARIOS = """RECEBIMENTOS SOMENTE EM CONTA JURÍDICA
Favorecido: Constelha (CNPJ: 38.067.474/0001-23)
Banco: Santander
Chave Pix: 38.067.474/0001-23"""

TERMOS_GERAIS = """1. O descarregamento é feito mediante pagamento de 100% do valor devido (salvo acordo prévio com diretoria).
2. Descarga somente ao lado do caminhão.
3. Taxa da maquininha de cartão é repassada ao cliente.
4. Não aceitamos alteração/devolução após início da produção.
5. Conferência (itens, medidas, qtd) é responsabilidade do cliente no ato da entrega.
6. Entregas seguem logística de formação de carga. Atrasos logísticos/pintura não geram responsabilidade civil.
7. O Cliente é responsável pelas medidas especificadas no pedido."""


class OrcamentoPDF(FPDF):
    """PDF personalizado para orçamentos."""

    def header(self):
        pass  # header customizado no conteúdo

    def footer(self):
        pass  # footer customizado no conteúdo

    # ─── helpers ─────────────────────────────────────────────
    def set_cor(self, rgb, draw=False, fill=False, text=False):
        r, g, b = rgb
        if draw:
            self.set_draw_color(r, g, b)
        if fill:
            self.set_fill_color(r, g, b)
        if text:
            self.set_text_color(r, g, b)

    def label_value(self, label: str, value: str, sub: str = "", w: float = 55):
        self.set_font("Helvetica", "B", 7)
        self.set_cor(COR_CINZA, text=True)
        self.cell(w, 4, label.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "B", 11)
        self.set_cor(COR_TEXTO, text=True)
        self.cell(w, 6, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if sub:
            self.set_font("Helvetica", "", 7)
            self.set_cor(COR_CINZA, text=True)
            self.cell(w, 4, sub, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)


class PDFGenerator:
    """Gera PDFs de orçamento profissionais."""

    def generate(
        self,
        numero: str,
        nome_cliente: str,
        itens: list[dict],
        valor_total: float,
        validade: str,
        observacoes: str = "",
    ) -> bytes:
        """
        Gera o PDF do orçamento e retorna os bytes.

        Args:
            numero: Número do orçamento (ex: ORC-202402191030)
            nome_cliente: Nome do cliente
            itens: Lista de itens [{produto, quantidade, unidade, preco_unitario, total}]
            valor_total: Valor total em reais
            validade: Data de validade formatada (ex: 26/02/2026)
            observacoes: Observações opcionais

        Returns:
            bytes do PDF gerado
        """
        try:
            pdf = OrcamentoPDF(orientation="P", unit="mm", format="A4")
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_margins(MARGIN, 15, MARGIN)
            pdf.add_page()

            data_emissao = datetime.now().strftime("%d/%m/%Y às %H:%M")
            eff_w = PAGE_W - 2 * MARGIN  # largura efetiva = 180mm

            # ──────────────────────────────────────────────────
            # HEADER: Empresa | Número do Orçamento
            # ──────────────────────────────────────────────────
            col_emp = eff_w * 0.60
            col_orc = eff_w * 0.40

            # Empresa
            x0 = MARGIN
            y0 = pdf.get_y()
            pdf.set_xy(x0, y0)
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_cor(COR_VERMELHO, text=True)
            pdf.cell(col_emp, 8, settings.company_name, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(x0)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_cor(COR_CINZA, text=True)
            pdf.cell(col_emp, 5, settings.company_tagline, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(x0)
            contato = ""
            if settings.company_phone:
                contato += f"Tel: {settings.company_phone}"
            if settings.company_email:
                contato += f"  |  {settings.company_email}"
            if contato:
                pdf.set_font("Helvetica", "", 8)
                pdf.cell(col_emp, 5, contato)

            # Orçamento (alinhado à direita, mesmo bloco)
            y_orc = y0
            pdf.set_xy(x0 + col_emp, y_orc)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_cor(COR_CINZA, text=True)
            pdf.cell(col_orc, 5, "Orcamento", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(x0 + col_emp)
            pdf.set_font("Helvetica", "B", 15)
            pdf.set_cor(COR_VERMELHO, text=True)
            pdf.cell(col_orc, 7, numero, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(x0 + col_emp)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_cor(COR_CINZA, text=True)
            pdf.cell(col_orc, 5, f"Emitido em {data_emissao}", align="R")

            # Linha separadora vermelha
            pdf.ln(7)
            pdf.set_cor(COR_VERMELHO, draw=True)
            pdf.set_line_width(0.8)
            pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
            pdf.ln(6)

            # ──────────────────────────────────────────────────
            # BANNER
            # ──────────────────────────────────────────────────
            pdf.set_cor(COR_VERMELHO, fill=True)
            pdf.set_fill_color(*COR_VERMELHO)
            pdf.set_text_color(*COR_BRANCO)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(eff_w, 10, "PROPOSTA COMERCIAL", fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(5)

            # ──────────────────────────────────────────────────
            # INFO BOXES: Cliente | Validade | Itens
            # ──────────────────────────────────────────────────
            n_itens = len(itens)
            box_w = eff_w / 3
            box_h = 22
            x_start = MARGIN
            y_box = pdf.get_y()

            for i, (label, val, sub) in enumerate([
                ("Cliente", nome_cliente, ""),
                ("Validade do orcamento", validade, "Precos sujeitos a reajuste"),
                ("Total de itens", f"{n_itens} produto{'s' if n_itens != 1 else ''}", ""),
            ]):
                bx = x_start + i * box_w
                pdf.set_fill_color(*COR_CINZA_CLARO)
                pdf.set_draw_color(*COR_BORDA)
                pdf.set_line_width(0.3)
                pdf.rect(bx, y_box, box_w - 1, box_h, style="FD")
                pdf.set_xy(bx + 3, y_box + 3)
                pdf.set_font("Helvetica", "B", 7)
                pdf.set_text_color(*COR_CINZA)
                pdf.cell(box_w - 4, 4, label.upper())
                pdf.set_xy(bx + 3, y_box + 8)
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*COR_TEXTO)
                pdf.cell(box_w - 4, 6, val)
                if sub:
                    pdf.set_xy(bx + 3, y_box + 15)
                    pdf.set_font("Helvetica", "", 7)
                    pdf.set_text_color(*COR_CINZA)
                    pdf.cell(box_w - 4, 4, sub)

            pdf.set_y(y_box + box_h + 5)

            # ──────────────────────────────────────────────────
            # TABELA DE ITENS
            # ──────────────────────────────────────────────────
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*COR_VERMELHO)
            pdf.cell(eff_w, 6, "Itens do Orcamento", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)

            # Cabeçalho da tabela
            col_widths = [eff_w * p for p in [0.44, 0.12, 0.12, 0.16, 0.16]]
            headers = ["Produto", "Unidade", "Qtd.", "Preco Unit.", "Total"]
            aligns = ["L", "C", "R", "R", "R"]

            pdf.set_fill_color(*COR_VERMELHO)
            pdf.set_text_color(*COR_BRANCO)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_line_width(0)
            for j, (hdr, cw, aln) in enumerate(zip(headers, col_widths, aligns)):
                pdf.cell(cw, 8, hdr, fill=True, align=aln)
            pdf.ln()

            # Linhas dos itens
            pdf.set_font("Helvetica", "", 9)
            pdf.set_draw_color(*COR_BORDA)
            pdf.set_line_width(0.2)
            for idx, item in enumerate(itens):
                fundo = COR_CINZA_CLARO if idx % 2 == 1 else COR_BRANCO
                pdf.set_fill_color(*fundo)
                pdf.set_text_color(*COR_TEXTO)

                row_vals = [
                    item.get("produto", ""),
                    item.get("unidade", ""),
                    f"{item.get('quantidade', 0):.2f}",
                    f"R$ {item.get('preco_unitario', 0):.2f}",
                    f"R$ {item.get('total', 0):.2f}",
                ]
                row_h = 7
                for j, (val, cw, aln) in enumerate(zip(row_vals, col_widths, aligns)):
                    if j == 4:
                        pdf.set_font("Helvetica", "B", 9)
                        pdf.set_text_color(*COR_VERMELHO)
                    else:
                        pdf.set_font("Helvetica", "", 9)
                        pdf.set_text_color(*COR_TEXTO)
                    pdf.cell(cw, row_h, val, fill=True, align=aln, border="B")
                pdf.ln()

            pdf.ln(5)

            # ──────────────────────────────────────────────────
            # TOTAL
            # ──────────────────────────────────────────────────
            total_box_w = 75
            x_total = PAGE_W - MARGIN - total_box_w
            y_total = pdf.get_y()
            pdf.set_fill_color(*COR_VERMELHO)
            pdf.rect(x_total, y_total, total_box_w, 20, style="F")
            pdf.set_xy(x_total + 3, y_total + 3)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*COR_BRANCO)
            pdf.cell(total_box_w - 6, 5, "VALOR TOTAL DA PROPOSTA", align="C")
            pdf.set_xy(x_total + 3, y_total + 9)
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(total_box_w - 6, 9, f"R$ {valor_total:,.2f}", align="C")
            pdf.set_y(y_total + 26)

            # ──────────────────────────────────────────────────
            # CONDIÇÕES COMERCIAIS & DADOS BANCÁRIOS
            # ──────────────────────────────────────────────────
            y_cond = pdf.get_y()
            half_w = (eff_w / 2) - 2

            # Lado Esquerdo: Dados Bancários
            pdf.set_fill_color(*COR_OBS_FUNDO)
            pdf.set_draw_color(*COR_OBS_BORDA)
            pdf.set_line_width(0.3)
            # Altura estimada para 4 linhas + título
            h_banco = 22
            pdf.rect(MARGIN, y_cond, half_w, h_banco, style="FD")
            
            pdf.set_xy(MARGIN + 2, y_cond + 2)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*COR_VERMELHO)
            pdf.cell(half_w, 4, "DADOS PARA PAGAMENTO", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            pdf.set_x(MARGIN + 2)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*COR_TEXTO)
            pdf.multi_cell(half_w - 4, 3.5, DADOS_BANCARIOS)

            # Lado Direito: Prazos (simplificado)
            x_right = MARGIN + half_w + 4
            pdf.set_xy(x_right, y_cond)
            pdf.set_fill_color(*COR_CINZA_CLARO)
            pdf.set_draw_color(*COR_BORDA)
            pdf.rect(x_right, y_cond, half_w, h_banco, style="FD")

            pdf.set_xy(x_right + 2, y_cond + 2)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*COR_CINZA)
            pdf.cell(half_w, 4, "PRAZOS E ENTREGAS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_x(x_right + 2)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*COR_TEXTO)
            pdf.multi_cell(half_w - 4, 3.5, "Frete: A consultar\nPrazo: A consultar\nPagamento: A combinar")

            pdf.set_y(y_cond + h_banco + 3)

            # ──────────────────────────────────────────────────
            # TERMOS E CONDIÇÕES
            # ──────────────────────────────────────────────────
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*COR_CINZA)
            pdf.cell(eff_w, 4, "TERMOS E CONDIÇÕES DE FORNECIMENTO", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            pdf.set_font("Helvetica", "", 6)  # Fonte bem pequena para caber
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(eff_w, 3, TERMOS_GERAIS)
            
            pdf.ln(3)

            # ──────────────────────────────────────────────────
            # OBSERVAÇÕES
            # ──────────────────────────────────────────────────
            if observacoes:
                pdf.set_fill_color(*COR_OBS_FUNDO)
                pdf.set_draw_color(*COR_OBS_BORDA)
                pdf.set_line_width(0.4)
                y_obs = pdf.get_y()
                # desenhar caixa (altura estimada)
                pdf.set_font("Helvetica", "", 9)
                obs_lines = pdf.multi_cell(eff_w - 10, 5, observacoes, dry_run=True, output="LINES")
                obs_h = len(obs_lines) * 5 + 14
                pdf.rect(MARGIN, y_obs, eff_w, obs_h, style="FD")
                pdf.set_xy(MARGIN + 5, y_obs + 4)
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(230, 126, 34)
                pdf.cell(eff_w - 10, 5, "Observacoes:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_x(MARGIN + 5)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*COR_TEXTO)
                pdf.multi_cell(eff_w - 10, 5, observacoes)
                pdf.ln(4)

            # ──────────────────────────────────────────────────
            # FOOTER
            # ──────────────────────────────────────────────────
            pdf.ln(4)
            pdf.set_draw_color(*COR_BORDA)
            pdf.set_line_width(0.4)
            pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*COR_CINZA)
            pdf.cell(eff_w / 2, 5, settings.company_name)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(eff_w / 2, 5, f"Valido ate {validade}", align="R",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if contato:
                pdf.set_font("Helvetica", "", 7)
                pdf.cell(eff_w / 2, 4, contato)
            pdf.cell(eff_w / 2, 4, "Precos sujeitos a alteracao sem aviso previo", align="R",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(200, 200, 200)
            pdf.cell(eff_w, 4,
                     f"Documento gerado automaticamente  -  {settings.company_name}  -  {data_emissao}",
                     align="C")

            # ──────────────────────────────────────────────────
            # SAÍDA
            # ──────────────────────────────────────────────────
            pdf_bytes = bytes(pdf.output())
            logger.info(f"PDF gerado: {numero} | {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Erro ao gerar PDF {numero}: {e}")
            raise PDFGenerationError(f"Falha na geracao do PDF: {e}")


# Instância global
pdf_generator = PDFGenerator()
