"""
Template HTML para geração do orçamento em PDF via xhtml2pdf.
Design profissional para empresa de telhas e portas metálicas.
CSS adaptado para compatibilidade com xhtml2pdf/ReportLab.
"""

TEMPLATE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; }

        body {
            font-family: Helvetica, Arial, sans-serif;
            font-size: 11pt;
            color: #1a1a2e;
            background: #fff;
        }

        .page {
            padding: 30px 36px;
        }

        /* === HEADER === */
        .header-table {
            width: 100%;
            border-bottom: 3px solid #c0392b;
            padding-bottom: 14px;
            margin-bottom: 18px;
        }
        .header-table td {
            vertical-align: top;
        }
        .company-name {
            font-size: 20pt;
            font-weight: bold;
            color: #c0392b;
        }
        .company-tagline {
            font-size: 10pt;
            color: #666;
            margin-top: 2px;
        }
        .company-contact {
            font-size: 9pt;
            color: #555;
            margin-top: 6px;
            line-height: 1.6;
        }
        .quote-block {
            text-align: right;
        }
        .quote-label {
            font-size: 9pt;
            color: #888;
            text-transform: uppercase;
        }
        .quote-number {
            font-size: 18pt;
            font-weight: bold;
            color: #c0392b;
        }
        .quote-date {
            font-size: 9pt;
            color: #666;
            margin-top: 4px;
        }

        /* === BANNER === */
        .banner {
            background-color: #c0392b;
            color: white;
            padding: 8px 16px;
            margin-bottom: 16px;
            font-size: 12pt;
            font-weight: bold;
        }

        /* === INFO BOXES === */
        .info-table {
            width: 100%;
            margin-bottom: 16px;
        }
        .info-table td {
            width: 33%;
            background-color: #f8f9fa;
            border: 1px solid #e5e5e5;
            padding: 10px 12px;
            vertical-align: top;
        }
        .info-label {
            font-size: 8pt;
            font-weight: bold;
            color: #888;
            text-transform: uppercase;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 4px;
            margin-bottom: 6px;
        }
        .info-value {
            font-size: 12pt;
            font-weight: bold;
            color: #1a1a2e;
        }
        .info-sub {
            font-size: 9pt;
            color: #777;
            margin-top: 2px;
        }

        /* === TABELA DE ITENS === */
        .items-title {
            font-size: 11pt;
            font-weight: bold;
            color: #c0392b;
            margin-bottom: 8px;
        }
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
        }
        .items-table thead tr {
            background-color: #c0392b;
            color: white;
        }
        .items-table thead th {
            padding: 8px 10px;
            font-size: 9pt;
            font-weight: bold;
            text-transform: uppercase;
            text-align: left;
        }
        .items-table thead th.right {
            text-align: right;
        }
        .items-table tbody tr.even {
            background-color: #fafafa;
        }
        .items-table tbody tr.odd {
            background-color: #ffffff;
        }
        .items-table tbody td {
            padding: 7px 10px;
            font-size: 10pt;
            border-bottom: 1px solid #eeeeee;
            color: #333;
            vertical-align: middle;
        }
        .items-table tbody td.right {
            text-align: right;
        }
        .items-table tbody td.total-col {
            text-align: right;
            font-weight: bold;
            color: #c0392b;
        }

        /* === TOTAL === */
        .total-wrapper {
            text-align: right;
            margin-bottom: 20px;
        }
        .total-box {
            background-color: #c0392b;
            color: white;
            padding: 12px 20px;
            display: inline-block;
        }
        .total-label {
            font-size: 9pt;
            font-weight: bold;
            text-transform: uppercase;
        }
        .total-value {
            font-size: 20pt;
            font-weight: bold;
            margin-top: 2px;
        }

        /* === CONDIÇÕES === */
        .cond-table {
            width: 100%;
            margin-bottom: 16px;
        }
        .cond-table td {
            width: 33%;
            border-left: 3px solid #c0392b;
            background-color: #f8f9fa;
            padding: 8px 12px;
            vertical-align: top;
        }
        .cond-label {
            font-size: 8pt;
            color: #888;
            text-transform: uppercase;
            font-weight: bold;
        }
        .cond-value {
            font-size: 11pt;
            font-weight: bold;
            color: #1a1a2e;
            margin-top: 2px;
        }

        /* === OBSERVAÇÕES === */
        .obs-box {
            background-color: #fffbf0;
            border: 1px solid #ffe082;
            padding: 10px 14px;
            margin-bottom: 16px;
            font-size: 10pt;
            color: #555;
        }
        .obs-title {
            font-weight: bold;
            color: #e67e22;
            margin-bottom: 4px;
            font-size: 10pt;
        }

        /* === FOOTER === */
        .footer-table {
            width: 100%;
            border-top: 1px solid #eeeeee;
            padding-top: 12px;
        }
        .footer-table td {
            vertical-align: top;
        }
        .footer-left {
            font-size: 9pt;
            color: #888;
            line-height: 1.6;
        }
        .footer-right {
            text-align: right;
            font-size: 9pt;
            color: #aaa;
        }
        .stamp {
            font-size: 8pt;
            color: #ccc;
            margin-top: 8px;
            text-align: center;
        }
    </style>
</head>
<body>
<div class="page">

    <!-- HEADER -->
    <table class="header-table">
        <tr>
            <td>
                <div class="company-name">{{ company_name }}</div>
                <div class="company-tagline">{{ company_tagline }}</div>
                <div class="company-contact">
                    {% if company_phone %}Tel: {{ company_phone }}{% endif %}
                    {% if company_email %} | {{ company_email }}{% endif %}
                </div>
            </td>
            <td>
                <div class="quote-block">
                    <div class="quote-label">Orçamento</div>
                    <div class="quote-number">{{ numero }}</div>
                    <div class="quote-date">Emitido em {{ data_emissao }}</div>
                </div>
            </td>
        </tr>
    </table>

    <!-- BANNER -->
    <div class="banner">PROPOSTA COMERCIAL</div>

    <!-- CLIENTE / VALIDADE / ITENS -->
    <table class="info-table">
        <tr>
            <td>
                <div class="info-label">Cliente</div>
                <div class="info-value">{{ nome_cliente }}</div>
            </td>
            <td style="padding-left: 8px;">
                <div class="info-label">Validade do Orçamento</div>
                <div class="info-value">{{ validade }}</div>
                <div class="info-sub">Preços sujeitos a reajuste após esta data</div>
            </td>
            <td style="padding-left: 8px;">
                <div class="info-label">Total de Itens</div>
                <div class="info-value">{{ itens | length }} produto{% if itens | length != 1 %}s{% endif %}</div>
            </td>
        </tr>
    </table>

    <!-- TABELA DE ITENS -->
    <div class="items-title">Itens do Orçamento</div>
    <table class="items-table">
        <thead>
            <tr>
                <th style="width:44%">Produto</th>
                <th style="width:12%; text-align:center">Unidade</th>
                <th class="right" style="width:12%">Qtd.</th>
                <th class="right" style="width:16%">Preço Unit.</th>
                <th class="right" style="width:16%">Total</th>
            </tr>
        </thead>
        <tbody>
            {% for item in itens %}
            <tr class="{{ 'even' if loop.index is even else 'odd' }}">
                <td>{{ item.produto }}</td>
                <td style="text-align:center">{{ item.unidade }}</td>
                <td class="right">{{ "%.2f"|format(item.quantidade) }}</td>
                <td class="right">R$ {{ "%.2f"|format(item.preco_unitario) }}</td>
                <td class="total-col">R$ {{ "%.2f"|format(item.total) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <!-- TOTAL -->
    <table width="100%" style="margin-bottom: 20px;">
        <tr>
            <td style="text-align: right;">
                <table style="background-color: #c0392b; color: white; padding: 12px 20px; display: inline-table;">
                    <tr>
                        <td>
                            <div class="total-label">Valor Total da Proposta</div>
                            <div class="total-value">R$ {{ "%.2f"|format(valor_total) }}</div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>

    <!-- CONDIÇÕES COMERCIAIS -->
    <table class="cond-table">
        <tr>
            <td>
                <div class="cond-label">Forma de Pagamento</div>
                <div class="cond-value">A combinar</div>
            </td>
            <td style="padding-left: 8px;">
                <div class="cond-label">Frete</div>
                <div class="cond-value">A consultar</div>
            </td>
            <td style="padding-left: 8px;">
                <div class="cond-label">Prazo de Entrega</div>
                <div class="cond-value">A consultar</div>
            </td>
        </tr>
    </table>

    <!-- OBSERVAÇÕES -->
    {% if observacoes %}
    <div class="obs-box">
        <div class="obs-title">Observações</div>
        {{ observacoes }}
    </div>
    {% endif %}

    <!-- FOOTER -->
    <table class="footer-table">
        <tr>
            <td class="footer-left">
                <strong>{{ company_name }}</strong><br>
                {% if company_phone %}Tel: {{ company_phone }}{% endif %}
                {% if company_email %} | {{ company_email }}{% endif %}
            </td>
            <td class="footer-right">
                Orçamento válido até <strong>{{ validade }}</strong><br>
                Preços sujeitos a alteração sem aviso prévio
            </td>
        </tr>
    </table>

    <div class="stamp">Documento gerado automaticamente • {{ company_name }} • {{ data_emissao }}</div>

</div>
</body>
</html>"""
