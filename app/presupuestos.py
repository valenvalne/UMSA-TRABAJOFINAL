from pathlib import Path
from datetime import datetime
import os
import json
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)

def format_currency(val):
    try:
        val = float(val)
        # Format as Argentine/Spanish standard: 10.000,00 or clean if zero decimals
        if val == int(val):
            return f"$ {int(val):,}".replace(",", ".")
        formatted = f"{val:,.2f}"
        main, dec = formatted.split(".")
        return f"$ {main.replace(',', '.')},{dec}"
    except Exception:
        return f"$ {val}"

def generate_presupuesto_pdf(
    cliente,
    productos,
    institucion="",
    observaciones="",
    validez="15 días corridos",
    iva_porcentaje=21.0,
    numero=None,
    output_dir=None,
):
    """
    Genera un presupuesto en PDF profesional utilizando ReportLab.
    Guarda el archivo físicamente en output_dir (por defecto files_storage/presupuestos).
    """
    if output_dir is None:
        from .services import STORAGE, ensure_module
        ensure_module("presupuestos")
        output_dir = STORAGE / "presupuestos"
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    if not numero:
        # Generar número secuencial / correlativo con timestamp
        count = len(list(output_dir.glob("*.pdf"))) + 1
        numero = f"UMSA-P-{now.year}-{count:04d}"

    filename = f"{numero}.pdf"
    filepath = output_dir / filename

    # Cálculos matemáticos rigurosos
    subtotal = 0.0
    items_calculados = []
    for idx, prod in enumerate(productos, 1):
        desc = str(prod.get("descripcion", prod.get("producto", f"Ítem {idx}"))).strip()
        try:
            cant = float(prod.get("cantidad", 1))
        except (ValueError, TypeError):
            cant = 1.0
        try:
            pu = float(prod.get("precio_unitario", prod.get("precio", 0)))
        except (ValueError, TypeError):
            pu = 0.0
        row_sub = cant * pu
        subtotal += row_sub
        items_calculados.append({
            "idx": idx,
            "descripcion": desc,
            "cantidad": int(cant) if cant == int(cant) else cant,
            "precio_unitario": pu,
            "subtotal": row_sub
        })

    try:
        iva_pct = float(iva_porcentaje)
    except (ValueError, TypeError):
        iva_pct = 21.0

    iva_monto = subtotal * (iva_pct / 100.0)
    total = subtotal + iva_monto

    # Construcción del PDF
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Presupuesto {numero} - UMSA",
        author="UMSA IA · Panel Administrativo",
    )

    styles = getSampleStyleSheet()

    # Colores corporativos
    c_primary = HexColor("#0f2b48")     # Navy azul oscuro UMSA
    c_accent = HexColor("#c92332")      # Rojo UMSA institucional
    c_teal = HexColor("#0d9488")        # Teal médico
    c_dark = HexColor("#1e293b")        # Slate oscuro
    c_muted = HexColor("#64748b")       # Gris texto secundario
    c_bg_light = HexColor("#f8fafc")    # Fondo suave
    c_border = HexColor("#cbd5e1")      # Bordes suaves

    # Estilos tipográficos
    style_header_title = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=c_primary,
    )
    style_header_sub = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=c_muted,
    )
    style_doc_type = ParagraphStyle(
        "DocType",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=c_accent,
        alignment=2, # Derecha
    )
    style_doc_meta = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        textColor=c_dark,
        alignment=2, # Derecha
    )
    style_section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=c_primary,
    )
    style_body = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=c_dark,
    )
    style_body_bold = ParagraphStyle(
        "BodyDarkBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=c_dark,
    )
    style_table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white,
        alignment=1, # Centrado
    )
    style_table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=c_dark,
    )
    style_table_cell_center = ParagraphStyle(
        "TableCellCenter",
        parent=style_table_cell,
        alignment=1,
    )
    style_table_cell_right = ParagraphStyle(
        "TableCellRight",
        parent=style_table_cell,
        alignment=2,
    )
    style_total_label = ParagraphStyle(
        "TotalLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.white,
        alignment=2,
    )
    style_total_val = ParagraphStyle(
        "TotalVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.white,
        alignment=2,
    )
    style_footer = ParagraphStyle(
        "FooterText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=c_muted,
        alignment=1,
    )

    story = []

    # 1. ENCABEZADO SUPERIOR (Marca UMSA + Datos de presupuesto)
    header_data = [
        [
            Paragraph("<b>UMSA CENTRO MÉDICO</b><br/><font size='8'>Panel Administrativo · Suministros & Servicios Médicos</font>", style_header_title),
            Paragraph(f"<b>PRESUPUESTO</b><br/><b>N°:</b> {numero}<br/><b>Fecha:</b> {now.strftime('%d/%m/%Y')}<br/><b>Validez:</b> {validez}", style_doc_meta)
        ]
    ]
    t_header = Table(header_data, colWidths=[10 * cm, 7.8 * cm])
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_header)

    story.append(HRFlowable(width="100%", thickness=2, color=c_accent, spaceBefore=4, spaceAfter=14))

    # 2. BLOQUE DE DATOS DEL CLIENTE / PROFESIONAL
    institucion_line = f"<b>Institución / Clínica:</b> {institucion}<br/>" if institucion else ""
    client_box_content = [
        [
            Paragraph("<b>DATOS DEL DESTINATARIO</b>", style_section_title),
            Paragraph("<b>CONDICIONES COMERCIALES</b>", style_section_title),
        ],
        [
            Paragraph(f"<b>Profesional / Cliente:</b> {cliente}<br/>{institucion_line}<b>Destino:</b> Uso profesional / Centro médico", style_body),
            Paragraph(f"<b>Período de Validez:</b> {validez}<br/><b>Forma de Pago:</b> A convenir / Transferencia<br/><b>Estado:</b> Presupuesto Oficial Emitido", style_body),
        ]
    ]
    t_client = Table(client_box_content, colWidths=[9.5 * cm, 8.3 * cm])
    t_client.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), c_bg_light),
        ("BOX", (0, 0), (-1, -1), 1, c_border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, c_border),
    ]))
    story.append(t_client)
    story.append(Spacer(1, 14))

    # 3. TABLA DE PRODUCTOS / SERVICIOS
    table_headers = [
        Paragraph("<b>#</b>", style_table_header),
        Paragraph("<b>Descripción del Producto / Servicio</b>", ParagraphStyle("THLeft", parent=style_table_header, alignment=0)),
        Paragraph("<b>Cantidad</b>", style_table_header),
        Paragraph("<b>Precio Unitario</b>", style_table_header),
        Paragraph("<b>Subtotal</b>", style_table_header),
    ]
    table_rows = [table_headers]

    for item in items_calculados:
        row = [
            Paragraph(str(item["idx"]), style_table_cell_center),
            Paragraph(item["descripcion"], style_table_cell),
            Paragraph(str(item["cantidad"]), style_table_cell_center),
            Paragraph(format_currency(item["precio_unitario"]), style_table_cell_right),
            Paragraph(format_currency(item["subtotal"]), style_table_cell_right),
        ]
        table_rows.append(row)

    # Anchos para 17.8 cm totales
    col_widths = [1.0 * cm, 8.8 * cm, 2.2 * cm, 2.8 * cm, 3.0 * cm]
    t_products = Table(table_rows, colWidths=col_widths, repeatRows=1)
    
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), c_primary),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
    ]
    # Filas alternadas suaves
    for r in range(1, len(table_rows)):
        if r % 2 == 0:
            t_style.append(("BACKGROUND", (0, r), (-1, r), c_bg_light))

    t_products.setStyle(TableStyle(t_style))
    story.append(t_products)
    story.append(Spacer(1, 10))

    # 4. CUADRO DE TOTALES (Alineado a la derecha)
    summary_data = [
        [
            Paragraph("<b>Subtotal:</b>", style_body_bold),
            Paragraph(format_currency(subtotal), ParagraphStyle("SubVal", parent=style_body, alignment=2))
        ],
        [
            Paragraph(f"<b>IVA ({iva_pct}%):</b>", style_body_bold),
            Paragraph(format_currency(iva_monto), ParagraphStyle("IvaVal", parent=style_body, alignment=2))
        ],
        [
            Paragraph("<b>TOTAL:</b>", style_total_label),
            Paragraph(format_currency(total), style_total_val)
        ]
    ]
    t_summary = Table(summary_data, colWidths=[4.2 * cm, 4.0 * cm])
    t_summary.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, 1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 1), 0.5, c_border),
        ("BACKGROUND", (0, 2), (-1, 2), c_accent),
        ("TOPPADDING", (0, 2), (-1, 2), 6),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 6),
        ("BOX", (0, 0), (-1, -1), 1, c_border),
    ]))

    # Contenedor para alinear a la derecha
    t_summary_align = Table([[None, t_summary]], colWidths=[9.6 * cm, 8.2 * cm])
    t_summary_align.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_summary_align)
    story.append(Spacer(1, 14))

    # 5. OBSERVACIONES Y TÉRMINOS
    obs_text = observaciones.strip() if observaciones else "Sin observaciones adicionales. Presupuesto emitido a solicitud del profesional."
    obs_data = [
        [Paragraph("<b>OBSERVACIONES Y CONDICIONES</b>", style_section_title)],
        [Paragraph(f"• <b>Observaciones:</b> {obs_text}", style_body)],
        [Paragraph(f"• <b>Validez de la cotización:</b> {validez}. Transcurrido este plazo, los precios pueden ser recalculados según disponibilidad.", style_body)],
        [Paragraph("• <b>Carácter del documento:</b> Cotización administrativa emitida por el Panel de Gestión UMSA IA. No constituye factura fiscal definitiva.", style_body)],
    ]
    t_obs = Table(obs_data, colWidths=[17.8 * cm])
    t_obs.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), c_bg_light),
        ("BOX", (0, 0), (-1, -1), 0.5, c_border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(KeepTogether(t_obs))
    story.append(Spacer(1, 18))

    # 6. FIRMA Y PIE
    signature_data = [
        [
            Paragraph("____________________________________<br/><b>Administración UMSA</b><br/><font size='7' color='#64748b'>Panel Administrativo Inteligente</font>", ParagraphStyle("Sig1", parent=style_body, alignment=1)),
            Paragraph("____________________________________<br/><b>Conforme Profesional / Destinatario</b><br/><font size='7' color='#64748b'>Firma y Aclaración</font>", ParagraphStyle("Sig2", parent=style_body, alignment=1)),
        ]
    ]
    t_sig = Table(signature_data, colWidths=[8.9 * cm, 8.9 * cm])
    t_sig.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(KeepTogether(t_sig))
    story.append(Spacer(1, 10))

    # Pie institucional
    story.append(Paragraph(
        "UMSA IA · Panel Administrativo Privado | Sistema independiente de gestión interna | Sede Central UMSA",
        style_footer
    ))

    # Construir PDF
    doc.build(story)

    # Actualizar índices
    try:
        from .services import update_index
        update_index("presupuestos")
        update_index("")
    except Exception:
        pass

    res_dict = {
        "numero": numero,
        "filename": filename,
        "rel_path": f"presupuestos/{filename}",
        "abs_path": str(filepath),
        "cliente": cliente,
        "institucion": institucion,
        "subtotal": subtotal,
        "iva_monto": iva_monto,
        "iva_porcentaje": iva_pct,
        "total": total,
        "fecha": now.strftime("%d/%m/%Y"),
        "validez": validez,
        "items": items_calculados,
        "download_url": f"/api/files/download/?path=presupuestos/{filename}",
        "estado": "Confirmado",
    }

    try:
        record_presupuesto_in_historial(res_dict, estado="Confirmado")
    except Exception:
        pass

    return res_dict


def get_historial_file_path():
    from .services import STORAGE
    return STORAGE / "presupuestos" / "presupuestos_historial.json"


def init_historial_from_storage():
    """
    Carga o inicializa el historial estructurado de presupuestos en files_storage/presupuestos/presupuestos_historial.json.
    Si el archivo no existe, lo inicializa a partir de las entradas reales de MEMORY.md
    y los archivos PDF ya generados físicamente.
    """
    from .services import STORAGE
    h_file = get_historial_file_path()
    if h_file.exists():
        try:
            data = json.loads(h_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass

    records = []
    seen_nums = set()

    # 1. Leer registros de memoria persistente de presupuestos
    mem_files = [
        STORAGE / "presupuestos" / "MEMORY.md",
        STORAGE / "MEMORY.md",
    ]
    mem_lines = []
    for mf in mem_files:
        if mf.exists():
            mem_lines.extend(mf.read_text(encoding="utf-8").splitlines())

    pat = re.compile(
        r"\[(?P<dt>\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}\].*?Presupuesto\s+(?P<num>UMSA-P-[\w-]+)\s+generado para\s+(?P<cli>[^:]+):\s+Total\s+\$(?P<tot>[\d\.]+)(?:\s+\((?P<items>\d+)\s+ítems\))?",
        re.IGNORECASE
    )

    for line in mem_lines:
        m = pat.search(line)
        if m:
            num = m.group("num")
            if num in seen_nums:
                continue
            seen_nums.add(num)
            dt_raw = m.group("dt")
            try:
                dt_obj = datetime.strptime(dt_raw, "%Y-%m-%d")
                fecha_formatted = dt_obj.strftime("%d/%m/%Y")
            except Exception:
                fecha_formatted = dt_raw
            tot = float(m.group("tot"))
            cli = m.group("cli").strip()
            item_count = int(m.group("items") or 1)
            pdf_name = f"{num}.pdf"

            records.append({
                "numero": num,
                "fecha": fecha_formatted,
                "fecha_iso": dt_raw,
                "cliente": cli,
                "institucion": "Centro Médico UMSA",
                "subtotal": tot,
                "iva_monto": 0.0,
                "iva_porcentaje": 0.0,
                "total": tot,
                "estado": "Confirmado",
                "validez": "15 días corridos",
                "items": [
                    {
                        "idx": 1,
                        "descripcion": f"Insumos médicos cotizados ({item_count} ítem{'s' if item_count > 1 else ''})",
                        "cantidad": item_count,
                        "precio_unitario": tot / item_count if item_count else tot,
                        "subtotal": tot,
                    }
                ],
                "filename": pdf_name,
                "rel_path": f"presupuestos/{pdf_name}",
                "download_url": f"/api/files/download/?path=presupuestos/{pdf_name}",
            })

    # 2. Agregar cualquier PDF existente en files_storage/presupuestos/ que no estuviese en MEMORY.md
    pdf_dir = STORAGE / "presupuestos"
    if pdf_dir.exists():
        for pdf in sorted(pdf_dir.glob("*.pdf"), reverse=True):
            num = pdf.stem
            if num not in seen_nums:
                seen_nums.add(num)
                mtime = datetime.fromtimestamp(pdf.stat().st_mtime)
                records.append({
                    "numero": num,
                    "fecha": mtime.strftime("%d/%m/%Y"),
                    "fecha_iso": mtime.strftime("%Y-%m-%d"),
                    "cliente": "Cliente Profesional",
                    "institucion": "Centro Médico UMSA",
                    "subtotal": 0.0,
                    "iva_monto": 0.0,
                    "iva_porcentaje": 0.0,
                    "total": 0.0,
                    "estado": "Confirmado",
                    "validez": "15 días corridos",
                    "items": [],
                    "filename": pdf.name,
                    "rel_path": f"presupuestos/{pdf.name}",
                    "download_url": f"/api/files/download/?path=presupuestos/{pdf.name}",
                })

    h_file.parent.mkdir(parents=True, exist_ok=True)
    h_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def record_presupuesto_in_historial(pres_data, estado="Confirmado"):
    """
    Guarda o actualiza un presupuesto en el historial persistente.
    """
    h_file = get_historial_file_path()
    historial = init_historial_from_storage()
    num = pres_data.get("numero")
    now = datetime.now()

    entry = {
        "numero": num,
        "fecha": pres_data.get("fecha") or now.strftime("%d/%m/%Y"),
        "fecha_iso": pres_data.get("fecha_iso") or now.strftime("%Y-%m-%d"),
        "cliente": pres_data.get("cliente") or "Cliente Profesional",
        "institucion": pres_data.get("institucion") or "Centro Médico UMSA",
        "subtotal": float(pres_data.get("subtotal", 0)),
        "iva_monto": float(pres_data.get("iva_monto", 0)),
        "iva_porcentaje": float(pres_data.get("iva_porcentaje", 0)),
        "total": float(pres_data.get("total", 0)),
        "estado": estado,
        "validez": pres_data.get("validez", "15 días corridos"),
        "items": pres_data.get("items", []),
        "filename": pres_data.get("filename") or f"{num}.pdf",
        "rel_path": pres_data.get("rel_path") or f"presupuestos/{num}.pdf",
        "download_url": pres_data.get("download_url") or f"/api/files/download/?path=presupuestos/{num}.pdf",
    }

    found = False
    for i, it in enumerate(historial):
        if it.get("numero") == num:
            historial[i] = entry
            found = True
            break
    if not found:
        historial.insert(0, entry)

    h_file.parent.mkdir(parents=True, exist_ok=True)
    h_file.write_text(json.dumps(historial, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def get_presupuestos_historial(filter_estado=None, search=None, fecha=None):
    """
    Retorna la lista de presupuestos con filtros opcionales por estado, búsqueda o período.
    """
    historial = init_historial_from_storage()
    results = []
    now = datetime.now()
    today_disp = now.strftime("%d/%m/%Y")
    today_iso = now.strftime("%Y-%m-%d")

    for p in historial:
        # Filtro por estado
        if filter_estado and filter_estado.strip().lower() not in ["todos", ""]:
            p_est = (p.get("estado") or "").strip().lower()
            if p_est != filter_estado.strip().lower():
                continue

        # Filtro por fecha
        if fecha:
            f_code = fecha.strip().lower()
            p_f = p.get("fecha", "")
            p_iso = p.get("fecha_iso", "")
            if f_code == "hoy":
                if p_f != today_disp and p_iso != today_iso:
                    continue
            elif f_code == "semana":
                try:
                    p_dt = datetime.strptime(p_iso, "%Y-%m-%d")
                    if (now - p_dt).days > 7:
                        continue
                except Exception:
                    pass
            elif f_code == "mes":
                try:
                    p_dt = datetime.strptime(p_iso, "%Y-%m-%d")
                    if p_dt.year != now.year or p_dt.month != now.month:
                        continue
                except Exception:
                    pass

        # Filtro de búsqueda (nombre, apellido, número de presupuesto, descripción)
        if search:
            s = search.strip().lower()
            num_match = s in (p.get("numero") or "").lower()
            cli_match = s in (p.get("cliente") or "").lower()
            items_match = any(s in str(it.get("descripcion", "")).lower() for it in p.get("items", []))
            if not (num_match or cli_match or items_match):
                continue

        # Enriquecer cada presupuesto con información calculada de pagos
        num = p.get("numero", "")
        try:
            from .pagos import get_presupuesto_pagos_summary
            p_summary = get_presupuesto_pagos_summary(num, total_presupuesto=float(p.get("total", 0.0)))
            p["total_pagado"] = p_summary["total_pagado"]
            p["saldo_pendiente"] = p_summary["saldo_pendiente"]
            p["estado_pago"] = p_summary["estado_pago"]
        except Exception:
            p["total_pagado"] = p.get("total_pagado", 0.0)
            p["saldo_pendiente"] = p.get("saldo_pendiente", float(p.get("total", 0.0)))
            p["estado_pago"] = p.get("estado_pago", "Pendiente")

        results.append(p)

    return results


def get_presupuesto_by_numero(numero):
    """
    Busca y retorna el detalle completo de un presupuesto por su número,
    incluyendo su historial de pagos y saldo pendiente.
    """
    if not numero:
        return None
    historial = init_historial_from_storage()
    target = numero.strip().lower()
    for p in historial:
        if (p.get("numero") or "").strip().lower() == target:
            try:
                from .pagos import get_presupuesto_pagos_summary
                p_summary = get_presupuesto_pagos_summary(p.get("numero", ""), total_presupuesto=float(p.get("total", 0.0)))
                p_copy = dict(p)
                p_copy["total_pagado"] = p_summary["total_pagado"]
                p_copy["saldo_pendiente"] = p_summary["saldo_pendiente"]
                p_copy["estado_pago"] = p_summary["estado_pago"]
                p_copy["pagos_detalle"] = p_summary["pagos"]
                return p_copy
            except Exception:
                pass
            return p
    return None


def get_dashboard_metrics():
    """
    Calcula con datos REALES las 4 métricas del Dashboard:
    1. Presupuestos de hoy (realizados durante el día actual)
    2. Presupuestos pendientes (aún no confirmados o en borrador)
    3. Productos disponibles (cantidad en inventario oficial)
    4. Total presupuestado (monto acumulado de presupuestos confirmados)
    """
    historial = init_historial_from_storage()
    now = datetime.now()
    today_disp = now.strftime("%d/%m/%Y")
    today_iso = now.strftime("%Y-%m-%d")

    # 1. Presupuestos de hoy
    pres_hoy = [
        p for p in historial
        if (p.get("fecha") == today_disp or p.get("fecha_iso") == today_iso)
        and p.get("estado") == "Confirmado"
    ]
    presupuestos_hoy = len(pres_hoy)

    # 2. Presupuestos pendientes
    pres_pendientes = [
        p for p in historial
        if p.get("estado") == "Pendiente"
    ]
    presupuestos_pendientes = len(pres_pendientes)

    # 3. Productos disponibles
    from .services import get_inventario
    inventario = get_inventario()
    productos_disponibles = len(inventario)

    # 4. Total presupuestado
    confirmados = [p for p in historial if p.get("estado") == "Confirmado"]
    total_presupuestado = sum(float(p.get("total", 0)) for p in confirmados)

    return {
        "presupuestos_hoy": presupuestos_hoy,
        "presupuestos_pendientes": presupuestos_pendientes,
        "productos_disponibles": productos_disponibles,
        "total_presupuestado": total_presupuestado,
        "total_presupuestado_formateado": format_currency(total_presupuestado),
        "tiene_presupuestos": len(confirmados) > 0,
        "total_registrados": len(historial),
    }


def search_global(query):
    """
    Búsqueda global unificada del panel administrativo:
    - Productos de inventario (nombre, presentación, precio, stock).
    - Presupuestos (por cliente, número, estado, fecha).
    - Consultas en lenguaje natural (ej: "¿Cuánto fue el último presupuesto de María?",
      "¿Cuánto sale el alcohol?").
    - Retorna datos reales determinísticos sin inventar información.
    """
    if not query or not str(query).strip():
        return {
            "ok": True,
            "query": "",
            "has_results": False,
            "message": "Ingrese un término de búsqueda.",
            "productos": [],
            "presupuestos": [],
            "natural_answer": None,
        }

    from .services import get_inventario
    from .local_assistant import normalize_text

    raw_query = str(query).strip()
    norm = normalize_text(raw_query)
    inventario = get_inventario()
    historial = init_historial_from_storage()

    matched_prods = []
    matched_pres = []
    natural_answer = None

    # 1. Búsqueda en Inventario
    for item in inventario:
        p_name = normalize_text(item.get("producto", ""))
        p_pres = normalize_text(item.get("presentacion", ""))
        # Match si la query está en producto o si el producto está en la query
        if norm in p_name or any(w in p_name for w in norm.split() if len(w) > 3) or p_name in norm:
            matched_prods.append(item)

    # 2. Búsqueda en Presupuestos
    # Limpiar prefijo "presupuesto" si busca "presupuesto 0001" o similar
    clean_search = re.sub(r"^(?:presupuesto|cotizacion|p-)\s*", "", norm).strip()
    for p in historial:
        cli = normalize_text(p.get("cliente", ""))
        num = normalize_text(p.get("numero", ""))
        # Match por cliente o número
        if (norm and (norm in cli or norm in num)) or (clean_search and (clean_search in num or clean_search in cli)):
            matched_pres.append(p)

    # 3. Interpretación de Lenguaje Natural
    # Pregunta por último presupuesto de alguien
    if "ultimo presupuesto" in norm or "presupuesto de" in norm or "cuanto fue" in norm or "cuanto gasto" in norm:
        # Extraer posible nombre del cliente
        for p in historial:
            cli_norm = normalize_text(p.get("cliente", ""))
            first_name = cli_norm.split()[0] if cli_norm else ""
            if (cli_norm and cli_norm in norm) or (first_name and len(first_name) >= 3 and first_name in norm):
                natural_answer = (
                    f"El último presupuesto registrado para **{p.get('cliente')}** es el **{p.get('numero')}** "
                    f"del {p.get('fecha')} por un total de **{format_currency(p.get('total'))}** ({p.get('estado')})."
                )
                if p not in matched_pres:
                    matched_pres.insert(0, p)
                break

    # Pregunta por precio de insumo
    if not natural_answer and ("cuanto sale" in norm or "cuanto cuesta" in norm or "precio de" in norm or "valor de" in norm):
        for item in inventario:
            p_name = normalize_text(item.get("producto", ""))
            if any(w in norm for w in p_name.split() if len(w) > 3):
                natural_answer = (
                    f"El precio oficial de **{item.get('producto')}** ({item.get('presentacion')}) "
                    f"es de **${item.get('precio_unitario')}** con stock **ILIMITADO** permanente."
                )
                if item not in matched_prods:
                    matched_prods.insert(0, item)
                break

    has_results = bool(matched_prods or matched_pres or natural_answer)
    message = None if has_results else "No encontré información relacionada con esa búsqueda."

    return {
        "ok": True,
        "query": raw_query,
        "has_results": has_results,
        "message": message,
        "productos": matched_prods[:6],
        "presupuestos": matched_pres[:10],
        "answer": natural_answer,
        "natural_answer": natural_answer,
    }


