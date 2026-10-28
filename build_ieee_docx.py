"""
Builds the IEEE Conference Paper Word Document (.docx) from ieee_conference_paper.html
with exact content, academic IEEE styling, tables, equations, and figures.
"""

import os
import sys
import re
from bs4 import BeautifulSoup, NavigableString, Tag
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

sys.stdout.reconfigure(encoding='utf-8')

def add_formatted_runs(p, soup_element, bold=False, italic=False, sub=False, sup=False,
                       font_name="Times New Roman", font_size=Pt(10), color=None):
    """Recursively adds runs with bold, italic, sub, sup to a docx paragraph."""
    for child in soup_element.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if not text:
                continue
            # Normalize non-breaking spaces
            text = text.replace('\xa0', ' ')
            run = p.add_run(text)
            run.font.name = font_name
            run.font.size = font_size
            if bold: run.bold = True
            if italic: run.italic = True
            if sub: run.font.subscript = True
            if sup: run.font.superscript = True
            if color: run.font.color.rgb = color
        elif isinstance(child, Tag):
            tag = child.name
            classes = child.get('class', [])
            nbold = bold or (tag in ['b', 'strong']) or ('abs-head' in classes)
            nitalic = italic or (tag in ['i', 'em']) or ('abs-head' in classes)
            nsub = sub or (tag == 'sub')
            nsup = sup or (tag == 'sup')
            if tag == 'br':
                p.add_run('\n')
            elif tag in ['span', 'div', 'p', 'b', 'strong', 'i', 'em', 'sub', 'sup']:
                add_formatted_runs(p, child, bold=nbold, italic=nitalic, sub=nsub, sup=nsup,
                                   font_name=font_name, font_size=font_size, color=color)

def format_ieee_table(table, col_widths=None):
    """Applies formal IEEE top/bottom borders, header formatting, and padding."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr

    # Table borders: top solid (0.75 pt = sz 6 or 8), bottom solid, no vertical, no inside horizontal
    borders = parse_xml(
        r'<w:tblBorders %s>'
        r'  <w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        r'  <w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        r'  <w:left w:val="none"/>'
        r'  <w:right w:val="none"/>'
        r'  <w:insideH w:val="none"/>'
        r'  <w:insideV w:val="none"/>'
        r'</w:tblBorders>' % nsdecls('w')
    )
    tblPr.append(borders)

    # Padding: top/bottom ~3.5 pt (70 dxa), left/right ~5 pt (100 dxa)
    tblCellMar = parse_xml(
        r'<w:tblCellMar %s>'
        r'  <w:top w:w="70" w:type="dxa"/>'
        r'  <w:bottom w:w="70" w:type="dxa"/>'
        r'  <w:left w:w="100" w:type="dxa"/>'
        r'  <w:right w:w="100" w:type="dxa"/>'
        r'</w:tblCellMar>' % nsdecls('w')
    )
    tblPr.append(tblCellMar)

    # Header row formatting and cantSplit
    for i, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(r'<w:cantSplit %s/>' % nsdecls('w')))
        if i == 0:
            trPr.append(parse_xml(r'<w:tblHeader %s/>' % nsdecls('w')))
            for cell in row.cells:
                tcPr = cell._tc.get_or_add_tcPr()
                # Bottom border for header row (0.75 pt)
                b_border = parse_xml(
                    r'<w:tcBorders %s><w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/></w:tcBorders>' % nsdecls('w')
                )
                tcPr.append(b_border)
                # Subtle light header background
                shd = parse_xml(r'<w:shd %s w:fill="F4F4F4"/>' % nsdecls('w'))
                tcPr.append(shd)

    # Set column widths
    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                if idx < len(row.cells):
                    row.cells[idx].width = width

def add_equation_block(doc, eq_node):
    """Creates a 1-row 2-col borderless table for equations with centered body and right-aligned num."""
    body_span = eq_node.find(class_='eq-body')
    num_span = eq_node.find(class_='eq-num')

    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        r'<w:tblBorders %s>'
        r'  <w:top w:val="none"/><w:bottom w:val="none"/><w:left w:val="none"/>'
        r'  <w:right w:val="none"/><w:insideH w:val="none"/><w:insideV w:val="none"/>'
        r'</w:tblBorders>' % nsdecls('w')
    )
    tblPr.append(borders)

    row = table.rows[0]
    row.cells[0].width = Inches(6.1)
    row.cells[1].width = Inches(0.9)

    # Body cell
    p_body = row.cells[0].paragraphs[0]
    p_body.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_body.paragraph_format.space_before = Pt(3)
    p_body.paragraph_format.space_after = Pt(3)
    if body_span:
        add_formatted_runs(p_body, body_span, font_name="Times New Roman", font_size=Pt(10))

    # Num cell
    p_num = row.cells[1].paragraphs[0]
    p_num.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_num.paragraph_format.space_before = Pt(3)
    p_num.paragraph_format.space_after = Pt(3)
    if num_span:
        run_num = p_num.add_run(num_span.get_text(strip=True))
        run_num.font.name = "Times New Roman"
        run_num.font.size = Pt(10)

    # Spacer paragraph after equation table for clean spacing
    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(2)
    p_spacer.paragraph_format.line_spacing = Pt(2)

def build_paper():
    doc = docx.Document()

    # Page setup: Standard Letter (8.5 x 11 in), 0.75 in margins
    for s in doc.sections:
        s.page_width = Inches(8.5)
        s.page_height = Inches(11.0)
        s.top_margin = Inches(0.75)
        s.bottom_margin = Inches(0.75)
        s.left_margin = Inches(0.75)
        s.right_margin = Inches(0.75)

    with open('ieee_conference_paper.html', 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # 1. Title Block
    title_div = soup.find(class_='paper-title')
    if title_div:
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_title.paragraph_format.space_before = Pt(0)
        p_title.paragraph_format.space_after = Pt(8)
        run_title = p_title.add_run(title_div.get_text(strip=True))
        run_title.font.name = "Times New Roman"
        run_title.font.size = Pt(18)
        run_title.bold = True

    authors_div = soup.find(class_='authors')
    if authors_div:
        p_auth = doc.add_paragraph()
        p_auth.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_auth.paragraph_format.space_before = Pt(0)
        p_auth.paragraph_format.space_after = Pt(3)
        run_auth = p_auth.add_run(authors_div.get_text(strip=True))
        run_auth.font.name = "Times New Roman"
        run_auth.font.size = Pt(10.5)

    affil_div = soup.find(class_='affil')
    if affil_div:
        p_affil = doc.add_paragraph()
        p_affil.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_affil.paragraph_format.space_before = Pt(0)
        p_affil.paragraph_format.space_after = Pt(14)
        run_affil = p_affil.add_run(affil_div.get_text(strip=True))
        run_affil.font.name = "Times New Roman"
        run_affil.font.size = Pt(9.5)
        run_affil.italic = True

    # 2. Abstract & Index Terms in a sleek bordered box
    abs_div = soup.find(class_='abstract-box')
    idx_div = soup.find(class_='index-terms')
    if abs_div or idx_div:
        box_table = doc.add_table(rows=1, cols=1)
        box_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = box_table.rows[0].cells[0]
        cell.width = Inches(7.0)

        # Border styling for abstract box
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(
            r'<w:tcBorders %s>'
            r'  <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            r'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            r'  <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            r'  <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            r'</w:tcBorders>' % nsdecls('w')
        )
        tcPr.append(borders)
        shd = parse_xml(r'<w:shd %s w:fill="FAFAFA"/>' % nsdecls('w'))
        tcPr.append(shd)

        # Cell margins
        mar = parse_xml(
            r'<w:tcMar %s>'
            r'  <w:top w:w="120" w:type="dxa"/>'
            r'  <w:bottom w:w="120" w:type="dxa"/>'
            r'  <w:left w:w="160" w:type="dxa"/>'
            r'  <w:right w:w="160" w:type="dxa"/>'
            r'</w:tcMar>' % nsdecls('w')
        )
        tcPr.append(mar)

        # Abstract paragraph
        if abs_div:
            p_abs = cell.paragraphs[0]
            p_abs.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_abs.paragraph_format.space_before = Pt(2)
            p_abs.paragraph_format.space_after = Pt(6)
            p_abs.paragraph_format.line_spacing = 1.15

            # Bold italic lead-in
            r_abs_lead = p_abs.add_run("Abstract—")
            r_abs_lead.font.name = "Times New Roman"
            r_abs_lead.font.size = Pt(9.5)
            r_abs_lead.bold = True
            r_abs_lead.italic = True

            # Extract body text without the abs-head span
            abs_head_span = abs_div.find(class_='abs-head')
            abs_text = ""
            for child in abs_div.children:
                if child != abs_head_span:
                    if isinstance(child, NavigableString):
                        abs_text += str(child)
                    elif isinstance(child, Tag):
                        abs_text += child.get_text()
            abs_text = abs_text.strip().replace('\xa0', ' ')
            r_abs_body = p_abs.add_run(" " + abs_text)
            r_abs_body.font.name = "Times New Roman"
            r_abs_body.font.size = Pt(9.5)

        # Index Terms paragraph
        if idx_div:
            p_idx = cell.add_paragraph()
            p_idx.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_idx.paragraph_format.space_before = Pt(0)
            p_idx.paragraph_format.space_after = Pt(2)
            p_idx.paragraph_format.line_spacing = 1.15

            # Bold italic lead-in
            r_idx_lead = p_idx.add_run("Index Terms—")
            r_idx_lead.font.name = "Times New Roman"
            r_idx_lead.font.size = Pt(9.5)
            r_idx_lead.bold = True
            r_idx_lead.italic = True

            idx_text = idx_div.get_text(strip=True)
            # Remove "Index Terms" and dash prefix
            idx_text = re.sub(r'^Index\s*Terms[\s—\-]*', '', idx_text).strip().replace('\xa0', ' ')
            r_idx_body = p_idx.add_run(idx_text)
            r_idx_body.font.name = "Times New Roman"
            r_idx_body.font.size = Pt(9.5)

        # Spacer after box
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(8)
        p_sp.paragraph_format.space_after = Pt(0)
        p_sp.paragraph_format.line_spacing = Pt(2)

    # 3. Process the sequential document items
    two_col = soup.find('div', class_='two-col')
    items = []

    def scan_node(node):
        for c in node.children:
            if not getattr(c, 'name', None):
                continue
            cls = c.get('class', [])
            tag = c.name
            if tag in ['h2', 'h3']:
                items.append(('HEADING', tag, c))
            elif 'tbl-wrap' in cls:
                items.append(('TABLE', 'tbl', c))
            elif 'eq-row' in cls:
                items.append(('EQ', 'eq', c))
            elif 'fig-wrap' in cls:
                items.append(('FIG', 'fig', c))
            elif 'ref-list' in cls:
                items.append(('REFS', 'refs', c))
            elif tag == 'p':
                items.append(('P', 'p', c))
            elif tag in ['div', 'section']:
                scan_node(c)

    scan_node(two_col)
    print(f"Loaded {len(items)} document body items.")

    # Table column width definitions (total ~6.8 - 7.0 in)
    table_widths_map = {
        0: [Inches(1.1), Inches(1.5), Inches(1.3), Inches(1.5), Inches(1.4)], # Table I
        1: [Inches(2.4), Inches(1.1), Inches(3.3)],                          # Table II
        2: [Inches(1.5), Inches(3.1), Inches(2.2)],                          # Table III
        3: [Inches(1.8), Inches(0.9), Inches(4.1)],                          # Table IV
        4: [Inches(1.8), Inches(2.3), Inches(2.7)],                          # Table V
        5: [Inches(1.5), Inches(2.3), Inches(3.0)],                          # Table VI
        6: [Inches(1.9), Inches(1.6), Inches(1.6), Inches(1.7)]              # Table VII
    }
    table_idx_counter = 0

    for item_type, subtype, elem in items:
        if item_type == 'HEADING':
            raw_text = elem.get_text(separator=' ', strip=True)
            raw_text = raw_text.replace('\xa0', ' ')
            raw_text = re.sub(r'\s+', ' ', raw_text)

            p_h = doc.add_paragraph()
            p_h.paragraph_format.keep_with_next = True

            if subtype == 'h2':
                # IEEE Section Heading (e.g. "I.  INTRODUCTION", "REFERENCES")
                p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_h.paragraph_format.space_before = Pt(14)
                p_h.paragraph_format.space_after = Pt(4)
                
                m = re.match(r'^([IVXLCDM]+\.)\s*(.*)$', raw_text)
                if m:
                    heading_text = f"{m.group(1)}  {m.group(2).upper()}"
                else:
                    heading_text = raw_text.upper()
                
                run = p_h.add_run(heading_text)
                run.font.name = "Times New Roman"
                run.font.size = Pt(10)
                run.bold = True

            elif subtype == 'h3':
                # IEEE Subsection Heading (e.g. "A.  Wind Farm Description")
                p_h.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p_h.paragraph_format.space_before = Pt(9)
                p_h.paragraph_format.space_after = Pt(3)

                m = re.match(r'^([A-Z]\.)\s*(.*)$', raw_text)
                if m:
                    heading_text = f"{m.group(1)}  {m.group(2)}"
                else:
                    heading_text = raw_text

                run = p_h.add_run(heading_text)
                run.font.name = "Times New Roman"
                run.font.size = Pt(10)
                run.bold = True
                run.italic = True

        elif item_type == 'P':
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_runs(p, elem, font_name="Times New Roman", font_size=Pt(10))

        elif item_type == 'EQ':
            add_equation_block(doc, elem)

        elif item_type == 'FIG':
            # Insert rendered pipeline diagram image
            png_path = os.path.abspath('figure1.png')
            if os.path.exists(png_path):
                p_fig = doc.add_paragraph()
                p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_fig.paragraph_format.space_before = Pt(10)
                p_fig.paragraph_format.space_after = Pt(4)
                p_fig.paragraph_format.keep_with_next = True
                run_img = p_fig.add_run()
                run_img.add_picture(png_path, width=Inches(6.6))

            # Figure caption below image
            cap_div = elem.find(class_='fig-cap')
            if cap_div:
                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p_cap.paragraph_format.space_before = Pt(2)
                p_cap.paragraph_format.space_after = Pt(12)
                p_cap.paragraph_format.line_spacing = 1.15

                cap_text = cap_div.get_text(separator=' ', strip=True).replace('\xa0', ' ')
                m = re.match(r'^(Fig\.\s*\d+\.)\s*(.*)$', cap_text)
                if m:
                    r1 = p_cap.add_run(m.group(1) + " ")
                    r1.font.name = "Times New Roman"
                    r1.font.size = Pt(9)
                    r1.bold = True
                    r2 = p_cap.add_run(m.group(2))
                    r2.font.name = "Times New Roman"
                    r2.font.size = Pt(9)
                else:
                    add_formatted_runs(p_cap, cap_div, font_name="Times New Roman", font_size=Pt(9))

        elif item_type == 'TABLE':
            cap_div = elem.find(class_='tbl-cap')
            if cap_div:
                cap_text = cap_div.get_text(separator=' ', strip=True).replace('\xa0', ' ')
                
                # IEEE Table caption format:
                # Line 1: TABLE I
                # Line 2: PER-TURBINE DATASET COVERAGE
                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_cap.paragraph_format.space_before = Pt(12)
                p_cap.paragraph_format.space_after = Pt(4)
                p_cap.paragraph_format.keep_with_next = True

                m = re.match(r'^(Table\s*[IVXLCDM]+)\.[\s—]*(.*)$', cap_text, re.IGNORECASE)
                if m:
                    line1 = m.group(1).upper()
                    line2 = m.group(2).upper()
                    r1 = p_cap.add_run(f"{line1}\n")
                    r1.font.name = "Times New Roman"
                    r1.font.size = Pt(9)
                    r1.bold = True
                    r2 = p_cap.add_run(line2)
                    r2.font.name = "Times New Roman"
                    r2.font.size = Pt(8.5)
                    r2.bold = True
                else:
                    r = p_cap.add_run(cap_text.upper())
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(9)
                    r.bold = True

            html_table = elem.find('table')
            if html_table:
                html_rows = html_table.find_all('tr')
                num_rows = len(html_rows)
                first_cells = html_rows[0].find_all(['th', 'td'])
                num_cols = len(first_cells)

                word_table = doc.add_table(rows=num_rows, cols=num_cols)
                widths = table_widths_map.get(table_idx_counter, [Inches(7.0 / num_cols)] * num_cols)
                table_idx_counter += 1

                for r_idx, h_row in enumerate(html_rows):
                    cells = h_row.find_all(['th', 'td'])
                    is_header = (r_idx == 0) or all(c.name == 'th' for c in cells)

                    for c_idx, cell_elem in enumerate(cells):
                        if c_idx >= num_cols:
                            break
                        w_cell = word_table.cell(r_idx, c_idx)
                        p_cell = w_cell.paragraphs[0]
                        p_cell.paragraph_format.space_before = Pt(2)
                        p_cell.paragraph_format.space_after = Pt(2)
                        p_cell.paragraph_format.line_spacing = 1.05

                        cell_txt = cell_elem.get_text(strip=True)
                        if is_header:
                            p_cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            add_formatted_runs(p_cell, cell_elem, bold=True,
                                               font_name="Times New Roman", font_size=Pt(8.5))
                        else:
                            if re.match(r'^[\d,\.]+(\s*%|\s*h)?$', cell_txt) or cell_txt in ['A0', 'A10', 'A11', 'A13', 'A21']:
                                p_cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            elif re.match(r'^\d+\s+of\s+\d+$', cell_txt):
                                p_cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            else:
                                p_cell.alignment = WD_ALIGN_PARAGRAPH.LEFT
                            add_formatted_runs(p_cell, cell_elem,
                                               font_name="Times New Roman", font_size=Pt(8.5))

                format_ieee_table(word_table, widths)

                p_post = doc.add_paragraph()
                p_post.paragraph_format.space_before = Pt(6)
                p_post.paragraph_format.space_after = Pt(0)
                p_post.paragraph_format.line_spacing = Pt(2)

        elif item_type == 'REFS':
            ol_items = elem.find_all('li')
            for li in ol_items:
                p_ref = doc.add_paragraph()
                p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p_ref.paragraph_format.left_indent = Inches(0.35)
                p_ref.paragraph_format.first_line_indent = Inches(-0.35)
                p_ref.paragraph_format.space_before = Pt(1)
                p_ref.paragraph_format.space_after = Pt(3)
                p_ref.paragraph_format.line_spacing = 1.15

                ref_num = li.find(class_='ref-num')
                if ref_num:
                    r_num = p_ref.add_run(ref_num.get_text(strip=True) + " ")
                    r_num.font.name = "Times New Roman"
                    r_num.font.size = Pt(9)

                ref_spans = [c for c in li.children if getattr(c, 'name', None) and 'ref-num' not in c.get('class', [])]
                if ref_spans:
                    for sp in ref_spans:
                        add_formatted_runs(p_ref, sp, font_name="Times New Roman", font_size=Pt(9))
                else:
                    for child in li.children:
                        if child != ref_num:
                            if isinstance(child, NavigableString):
                                r = p_ref.add_run(str(child))
                                r.font.name = "Times New Roman"
                                r.font.size = Pt(9)
                            elif isinstance(child, Tag):
                                add_formatted_runs(p_ref, child, font_name="Times New Roman", font_size=Pt(9))

    out_file = 'ieee_conference_paper.docx'
    doc.save(out_file)
    print(f"Document saved successfully as '{out_file}' (Size: {os.path.getsize(out_file)} bytes)")

if __name__ == '__main__':
    build_paper()
