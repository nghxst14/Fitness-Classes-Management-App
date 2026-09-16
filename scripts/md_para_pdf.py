"""
Converte um documento Markdown deste projeto num PDF legível.

Existe para os documentos que são para PESSOAS lerem fora do editor de código
— o MANUAL.md (para o Sérgio) e o REUNIAO-SERGIO.md. O Markdown continua a ser
a fonte da verdade e fica no Git; o PDF é gerado a partir dele, para não haver
duas versões a divergir.

Uso:
    python scripts/md_para_pdf.py MANUAL.md
    python scripts/md_para_pdf.py MANUAL.md -o algures/manual.pdf

Precisa do reportlab, que NÃO está no requirements.txt de propósito — a app não
precisa dele, é só uma ferramenta. Instala-o à parte se for preciso:
    pip install reportlab

Suporta o que estes documentos usam: títulos, parágrafos, listas com marcas e
numeradas, tabelas, citações, blocos de código, linhas horizontais, e negrito,
itálico e `código` dentro do texto.
"""
import argparse
import html
import re
import sys
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        KeepTogether,
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:
    sys.exit(
        "Falta o reportlab. Instala com:  pip install reportlab\n"
        "(não está no requirements.txt porque a app não precisa dele)"
    )

# Paleta da marca (ver static/img/brand/MARCA.md). No papel, o fundo é branco e
# o verde vivo do ecrã fica ilegível — usa-se o verde escuro.
VERDE = colors.HexColor("#337418")
PRETO = colors.HexColor("#1A1A1A")
CINZA = colors.HexColor("#5A5F57")
LINHA = colors.HexColor("#D8DBD3")
FUNDO_CODIGO = colors.HexColor("#F2F4EF")


def estilos():
    base = getSampleStyleSheet()
    normal = ParagraphStyle(
        "corpo", parent=base["Normal"], fontName="Helvetica", fontSize=10,
        leading=14.5, textColor=PRETO, spaceAfter=7, alignment=TA_LEFT,
    )
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=normal, fontName="Helvetica-Bold", fontSize=22,
            leading=26, textColor=PRETO, spaceAfter=4, spaceBefore=0,
        ),
        "h1": ParagraphStyle(
            "h1", parent=normal, fontName="Helvetica-Bold", fontSize=15,
            leading=19, textColor=VERDE, spaceBefore=20, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2", parent=normal, fontName="Helvetica-Bold", fontSize=12,
            leading=16, textColor=PRETO, spaceBefore=14, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3", parent=normal, fontName="Helvetica-Bold", fontSize=10.5,
            leading=14, textColor=CINZA, spaceBefore=10, spaceAfter=4,
        ),
        "corpo": normal,
        "lista": ParagraphStyle("lista", parent=normal, spaceAfter=3),
        "citacao": ParagraphStyle(
            "citacao", parent=normal, leftIndent=10, textColor=CINZA,
            borderPadding=(6, 6, 6, 6), backColor=FUNDO_CODIGO,
            borderColor=LINHA, borderWidth=0.5, spaceBefore=6, spaceAfter=8,
        ),
        "codigo": ParagraphStyle(
            "codigo", parent=normal, fontName="Courier", fontSize=8.5,
            leading=11.5, backColor=FUNDO_CODIGO, borderColor=LINHA,
            borderWidth=0.5, borderPadding=(6, 6, 6, 6),
            spaceBefore=5, spaceAfter=8,
        ),
        "celula": ParagraphStyle("celula", parent=normal, fontSize=9, leading=12,
                                 spaceAfter=0),
        "celula_cab": ParagraphStyle("celula_cab", parent=normal, fontSize=9,
                                     leading=12, spaceAfter=0,
                                     fontName="Helvetica-Bold"),
    }


# As fontes base do PDF (Helvetica, Courier) não têm emoji nem símbolos fora
# do alfabeto ocidental: sairiam como quadrados pretos. No Markdown eles ficam
# — no GitHub e no editor aparecem bem, e ajudam a ler. Aqui, alguns viram
# texto e os restantes desaparecem; a formatação a negrito à volta já os
# substitui como sinal de aviso.
EMOJI_PARA_TEXTO = {
    "⚠️": "", "⚠": "", "📱": "", "✓": "-", "✕": "x", "→": "->", "←": "<-",
}
SEM_GLIFO = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002190-\U000021FF"
    "\U00002600-\U000027BF" "\U0000FE00-\U0000FE0F" "]"
)


def limpar_simbolos(texto):
    for simbolo, substituto in EMOJI_PARA_TEXTO.items():
        texto = texto.replace(simbolo, substituto)
    texto = SEM_GLIFO.sub("", texto)
    return re.sub(r"  +", " ", texto).strip()


def inline(texto):
    """Converte a formatação dentro de uma linha para as marcas do reportlab."""
    t = html.escape(limpar_simbolos(texto))
    # `código` primeiro: o conteúdo não deve ser interpretado como negrito.
    t = re.sub(r"`([^`]+)`",
               r'<font face="Courier" size="9">\1</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    # Links: fica o texto, que num papel é o que interessa. A excepção são os
    # endereços verdadeiros (http), que se mantêm visíveis.
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    return t


def tabela(linhas, est, largura):
    """Constrói uma tabela a partir das linhas em Markdown (| a | b |)."""
    dados = []
    for i, linha in enumerate(linhas):
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if i == 1 and all(re.fullmatch(r":?-{2,}:?", c) for c in celulas if c):
            continue  # a linha de separação
        estilo = est["celula_cab"] if i == 0 else est["celula"]
        dados.append([Paragraph(inline(c), estilo) for c in celulas])
    if not dados:
        return None
    n = max(len(linha) for linha in dados)
    for linha in dados:
        while len(linha) < n:
            linha.append(Paragraph("", est["celula"]))
    t = Table(dados, colWidths=[largura / n] * n, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FUNDO_CODIGO),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, VERDE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, LINHA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def converter(md, est, largura):
    flow, i = [], 0
    linhas = md.split("\n")
    marcas, numeros = [], []

    def fechar_listas():
        nonlocal marcas, numeros
        for conjunto, marcador in ((marcas, "bullet"), (numeros, "1")):
            if conjunto:
                flow.append(ListFlowable(
                    [ListItem(Paragraph(x, est["lista"]), leftIndent=14)
                     for x in conjunto],
                    bulletType=marcador, leftIndent=16,
                    bulletFontSize=8, bulletColor=VERDE,
                ))
                flow.append(Spacer(1, 4))
                conjunto.clear()

    while i < len(linhas):
        linha = linhas[i]
        nu = linha.strip()

        if nu.startswith("```"):
            fechar_listas()
            i += 1
            bloco = []
            while i < len(linhas) and not linhas[i].strip().startswith("```"):
                bloco.append(html.escape(linhas[i]))
                i += 1
            if bloco:
                flow.append(Paragraph("<br/>".join(bloco), est["codigo"]))
            i += 1
            continue

        if not nu:
            fechar_listas()
            i += 1
            continue

        if re.fullmatch(r"(---+|\*\*\*+|___+)", nu):
            fechar_listas()
            flow.append(Spacer(1, 6))
            flow.append(HRFlowable(width="100%", thickness=0.6, color=LINHA))
            flow.append(Spacer(1, 6))
            i += 1
            continue

        if nu.startswith("|") and i + 1 < len(linhas) and "|" in linhas[i + 1]:
            fechar_listas()
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            t = tabela(bloco, est, largura)
            if t:
                flow.append(Spacer(1, 4))
                flow.append(t)
                flow.append(Spacer(1, 10))
            continue

        cab = re.match(r"^(#{1,6})\s+(.*)", nu)
        if cab:
            fechar_listas()
            nivel, texto = len(cab.group(1)), cab.group(2)
            # Tira as âncoras do índice, que em papel não servem.
            texto = re.sub(r"\s*\{#[^}]+\}", "", texto)
            chave = {1: "titulo", 2: "h1", 3: "h2"}.get(nivel, "h3")
            p = Paragraph(inline(texto), est[chave])
            # Um título nunca deve ficar sozinho no fim de uma página.
            flow.append(p if nivel == 1 else KeepTogether([p, Spacer(1, 1)]))
            i += 1
            continue

        if nu.startswith(">"):
            fechar_listas()
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith(">"):
                bloco.append(linhas[i].strip().lstrip(">").strip())
                i += 1
            flow.append(Paragraph(inline(" ".join(bloco)), est["citacao"]))
            continue

        m = re.match(r"^[-*]\s+(.*)", nu)
        if m:
            if numeros:
                fechar_listas()
            marcas.append(inline(m.group(1)))
            i += 1
            continue

        m = re.match(r"^\d+\.\s+(.*)", nu)
        if m:
            if marcas:
                fechar_listas()
            numeros.append(inline(m.group(1)))
            i += 1
            continue

        fechar_listas()
        # Junta as linhas seguidas num parágrafo só (o Markdown quebra a 80
        # colunas, mas no PDF a largura é outra).
        bloco = []
        while i < len(linhas) and linhas[i].strip() and not re.match(
            r"^(#{1,6}\s|>|\||```|[-*]\s|\d+\.\s|---+$)", linhas[i].strip()
        ):
            bloco.append(linhas[i].strip())
            i += 1
        flow.append(Paragraph(inline(" ".join(bloco)), est["corpo"]))

    fechar_listas()
    return flow


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(2 * cm, 1.3 * cm, "RESTART NOW")
    canvas.drawRightString(A4[0] - 2 * cm, 1.3 * cm, f"{doc.page}")
    canvas.setStrokeColor(LINHA)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.7 * cm, A4[0] - 2 * cm, 1.7 * cm)
    canvas.restoreState()


def main():
    ap = argparse.ArgumentParser(description="Converte um .md deste projeto em PDF.")
    ap.add_argument("origem", help="o ficheiro Markdown")
    ap.add_argument("-o", "--saida", help="o PDF a criar (por defeito, ao lado)")
    args = ap.parse_args()

    origem = Path(args.origem)
    if not origem.exists():
        sys.exit(f"Não encontrei {origem}")
    saida = Path(args.saida) if args.saida else origem.with_suffix(".pdf")

    margem = 2 * cm
    doc = SimpleDocTemplate(
        str(saida), pagesize=A4,
        leftMargin=margem, rightMargin=margem,
        topMargin=1.8 * cm, bottomMargin=2.2 * cm,
        title=origem.stem, author="RESTART NOW",
    )
    est = estilos()
    flow = converter(origem.read_text(encoding="utf-8"), est,
                     A4[0] - 2 * margem)
    doc.build(flow, onFirstPage=rodape, onLaterPages=rodape)
    print(f"{saida}  ({saida.stat().st_size / 1024:.0f} KB, {doc.page} páginas)")


if __name__ == "__main__":
    main()
