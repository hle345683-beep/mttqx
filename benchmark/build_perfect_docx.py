import os, sys, json, shutil, zipfile
import xml.etree.ElementTree as ET
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

W_NS   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP_NS  = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS   = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
R_NS   = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_NS = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace('w', W_NS)
ET.register_namespace('wp', WP_NS)
ET.register_namespace('a', A_NS)
ET.register_namespace('pic', PIC_NS)
ET.register_namespace('r', R_NS)

def wtag(name):
    return f"{{{W_NS}}}{name}"

def make_run(text, bold=False, italic=False, vert=None, style=None, no_proof=False, web_hidden=False):
    r = ET.Element(wtag('r'))
    if any([bold, italic, vert, style, no_proof, web_hidden]):
        rPr = ET.SubElement(r, wtag('rPr'))
        if style:
            ET.SubElement(rPr, wtag('rStyle'), {wtag('val'): style})
        if bold:
            ET.SubElement(rPr, wtag('b'))
        if italic:
            ET.SubElement(rPr, wtag('i'))
        if no_proof:
            ET.SubElement(rPr, wtag('noProof'))
        if web_hidden:
            ET.SubElement(rPr, wtag('webHidden'))
        if vert:
            ET.SubElement(rPr, wtag('vertAlign'), {wtag('val'): vert})
    t = ET.SubElement(r, wtag('t'))
    if text.startswith(' ') or text.endswith(' '):
        t.set(f"{{{XML_NS}}}space", "preserve")
    t.text = text
    return r

def make_para(runs_spec=None, style=None, jc=None, first_line='720', left=None, hanging=None,
              num_id=None, ilvl='0', page_break=False, keep_next=False, keep_lines=False,
              bm_id=None, bm_name=None, tabs=None, space_before=None, space_after=None):
    """
    runs_spec: list of tuples (text, dict_opts) or plain strings, or ('TAB', {})
    """
    p = ET.Element(wtag('p'))
    pPr = ET.SubElement(p, wtag('pPr'))
    if style:
        ET.SubElement(pPr, wtag('pStyle'), {wtag('val'): style})
    if page_break:
        ET.SubElement(pPr, wtag('pageBreakBefore'))
    if keep_next:
        ET.SubElement(pPr, wtag('keepNext'))
    if keep_lines:
        ET.SubElement(pPr, wtag('keepLines'))
    if num_id is not None:
        numPr = ET.SubElement(pPr, wtag('numPr'))
        ET.SubElement(numPr, wtag('ilvl'), {wtag('val'): str(ilvl)})
        ET.SubElement(numPr, wtag('numId'), {wtag('val'): str(num_id)})
    if tabs:
        tabs_el = ET.SubElement(pPr, wtag('tabs'))
        for t_val, t_pos, t_leader in tabs:
            attrib = {wtag('val'): t_val, wtag('pos'): str(t_pos)}
            if t_leader:
                attrib[wtag('leader')] = t_leader
            ET.SubElement(tabs_el, wtag('tab'), attrib)
    if space_before is not None or space_after is not None:
        sp_attr = {}
        if space_before is not None:
            sp_attr[wtag('before')] = str(space_before)
        if space_after is not None:
            sp_attr[wtag('after')] = str(space_after)
        ET.SubElement(pPr, wtag('spacing'), sp_attr)
    ind_attr = {}
    if left is not None:
        ind_attr[wtag('left')] = str(left)
    if hanging is not None:
        ind_attr[wtag('hanging')] = str(hanging)
    if first_line is not None and hanging is None:
        ind_attr[wtag('firstLine')] = str(first_line)
    if ind_attr:
        ET.SubElement(pPr, wtag('ind'), ind_attr)
    if jc:
        ET.SubElement(pPr, wtag('jc'), {wtag('val'): jc})

    if bm_id is not None and bm_name is not None:
        ET.SubElement(p, wtag('bookmarkStart'), {wtag('id'): str(bm_id), wtag('name'): bm_name})

    if runs_spec:
        for item in runs_spec:
            if isinstance(item, str):
                p.append(make_run(item))
            elif isinstance(item, tuple):
                txt, opts = item
                if txt == '__TAB__':
                    r = ET.SubElement(p, wtag('r'))
                    ET.SubElement(r, wtag('tab'))
                else:
                    p.append(make_run(txt, **opts))

    if bm_id is not None and bm_name is not None:
        ET.SubElement(p, wtag('bookmarkEnd'), {wtag('id'): str(bm_id)})

    return p

def make_heading(text, level=1, bm_id=101, bm_name="_Toc3000001", page_break=False, unnumbered=False):
    if level == 1:
        if unnumbered:
            return make_para([text], style='Heading1', jc='center', first_line=None, left='2155', hanging='2155',
                             num_id='0', ilvl='0', page_break=page_break, bm_id=bm_id, bm_name=bm_name)
        return make_para([text], style='Heading1', jc='center', first_line=None,
                         page_break=page_break, bm_id=bm_id, bm_name=bm_name)
    elif level == 2:
        return make_para([text], style='Heading2', first_line=None, keep_next=True, bm_id=bm_id, bm_name=bm_name)
    else:
        return make_para([text], style='Heading3', first_line=None, keep_next=True, bm_id=bm_id, bm_name=bm_name)

def make_caption(kind, chap_num, seq_num, title_text, bm_id=None, bm_name=None):
    """
    kind: 'Hình' or 'Bảng'
    Uses STYLEREF 1 \\s and SEQ Hình/Bảng \\* ARABIC \\s 1 exactly like Mẫu báo cáo
    """
    p = ET.Element(wtag('p'))
    pPr = ET.SubElement(p, wtag('pPr'))
    ET.SubElement(pPr, wtag('pStyle'), {wtag('val'): 'Caption'})

    if bm_id is not None and bm_name is not None:
        ET.SubElement(p, wtag('bookmarkStart'), {wtag('id'): str(bm_id), wtag('name'): bm_name})

    p.append(make_run(f"{kind} "))

    fld1 = ET.SubElement(p, wtag('fldSimple'), {wtag('instr'): ' STYLEREF 1 \\s '})
    fld1.append(make_run(str(chap_num), no_proof=True))

    p.append(make_run("."))

    fld2 = ET.SubElement(p, wtag('fldSimple'), {wtag('instr'): f' SEQ {kind} \\* ARABIC \\s 1 '})
    fld2.append(make_run(str(seq_num), no_proof=True))

    p.append(make_run(f". {title_text}"))

    if bm_id is not None and bm_name is not None:
        ET.SubElement(p, wtag('bookmarkEnd'), {wtag('id'): str(bm_id)})

    return p

def make_image_para(rid, doc_id, filename, descr, img_path, max_width_emu=5580000, max_height_emu=4350000):
    with Image.open(img_path) as im:
        w_px, h_px = im.size
    aspect = h_px / float(w_px)
    cx = max_width_emu
    cy = int(cx * aspect)
    if cy > max_height_emu:
        cy = max_height_emu
        cx = int(cy / aspect)

    xml_str = f'''<w:p xmlns:w="{W_NS}" xmlns:wp="{WP_NS}" xmlns:a="{A_NS}" xmlns:pic="{PIC_NS}" xmlns:r="{R_NS}">
      <w:pPr>
        <w:keepNext/>
        <w:spacing w:before="120" w:after="60"/>
        <w:ind w:firstLine="0"/>
        <w:jc w:val="center"/>
      </w:pPr>
      <w:r>
        <w:rPr><w:noProof/></w:rPr>
        <w:drawing>
          <wp:inline distT="0" distB="0" distL="0" distR="0">
            <wp:extent cx="{cx}" cy="{cy}"/>
            <wp:effectExtent l="0" t="0" r="0" b="0"/>
            <wp:docPr id="{doc_id}" name="Picture {doc_id}" descr="{descr}"/>
            <wp:cNvGraphicFramePr>
              <a:graphicFrameLocks noChangeAspect="1"/>
            </wp:cNvGraphicFramePr>
            <a:graphic>
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic>
                  <pic:nvPicPr>
                    <pic:cNvPr id="{doc_id}" name="{filename}" descr="{descr}"/>
                    <pic:cNvPicPr/>
                  </pic:nvPicPr>
                  <pic:blipFill>
                    <a:blip r:embed="{rid}"/>
                    <a:stretch><a:fillRect/></a:stretch>
                  </pic:blipFill>
                  <pic:spPr>
                    <a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                  </pic:spPr>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:inline>
        </w:drawing>
      </w:r>
    </w:p>'''
    return ET.fromstring(xml_str)

def make_table(col_widths, headers, rows, col_aligns=None, keep_with_caption=True):
    total_w = sum(col_widths)
    tbl = ET.Element(wtag('tbl'))
    tblPr = ET.SubElement(tbl, wtag('tblPr'))
    ET.SubElement(tblPr, wtag('tblStyle'), {wtag('val'): 'TableGrid'})
    ET.SubElement(tblPr, wtag('tblW'), {wtag('w'): str(total_w), wtag('type'): 'dxa'})
    ET.SubElement(tblPr, wtag('jc'), {wtag('val'): 'center'})
    ET.SubElement(tblPr, wtag('tblLayout'), {wtag('type'): 'fixed'})
    ET.SubElement(tblPr, wtag('tblLook'), {
        wtag('val'): '04A0', wtag('firstRow'): '1', wtag('lastRow'): '0',
        wtag('firstColumn'): '1', wtag('lastColumn'): '0', wtag('noHBand'): '0', wtag('noVBand'): '1'
    })

    tblGrid = ET.SubElement(tbl, wtag('tblGrid'))
    for w in col_widths:
        ET.SubElement(tblGrid, wtag('gridCol'), {wtag('w'): str(w)})

    # Header row
    tr_h = ET.SubElement(tbl, wtag('tr'))
    trPr_h = ET.SubElement(tr_h, wtag('trPr'))
    ET.SubElement(trPr_h, wtag('cantSplit'))
    ET.SubElement(trPr_h, wtag('tblHeader'))
    for idx, h_text in enumerate(headers):
        tc = ET.SubElement(tr_h, wtag('tc'))
        tcPr = ET.SubElement(tc, wtag('tcPr'))
        ET.SubElement(tcPr, wtag('tcW'), {wtag('w'): str(col_widths[idx]), wtag('type'): 'dxa'})
        ET.SubElement(tcPr, wtag('shd'), {wtag('val'): 'clear', wtag('color'): 'auto', wtag('fill'): 'E7E6E6', wtag('themeFill'): 'background2'})
        ET.SubElement(tcPr, wtag('vAlign'), {wtag('val'): 'center'})
        p = make_para([(h_text, {'bold': True})], first_line='0', jc='center', keep_next=True, space_before=40, space_after=40)
        tc.append(p)

    # Data rows
    for r_idx, row in enumerate(rows):
        tr = ET.SubElement(tbl, wtag('tr'))
        trPr = ET.SubElement(tr, wtag('trPr'))
        ET.SubElement(trPr, wtag('cantSplit'))
        is_last = (r_idx == len(rows) - 1)
        for c_idx, cell_val in enumerate(row):
            tc = ET.SubElement(tr, wtag('tc'))
            tcPr = ET.SubElement(tc, wtag('tcPr'))
            ET.SubElement(tcPr, wtag('tcW'), {wtag('w'): str(col_widths[c_idx]), wtag('type'): 'dxa'})
            ET.SubElement(tcPr, wtag('vAlign'), {wtag('val'): 'center'})
            align = col_aligns[c_idx] if col_aligns else 'center'
            if isinstance(cell_val, list):
                runs = cell_val
            else:
                runs = [str(cell_val)]
            p = make_para(runs, first_line='0', jc=align, keep_next=(is_last and keep_with_caption), space_before=40, space_after=40)
            tc.append(p)

    return tbl

def make_tof_entry(caption_full_text, bm_name, page_str, is_first_for_kind=None):
    p = ET.Element(wtag('p'))
    pPr = ET.SubElement(p, wtag('pPr'))
    ET.SubElement(pPr, wtag('pStyle'), {wtag('val'): 'TableofFigures'})
    tabs = ET.SubElement(pPr, wtag('tabs'))
    ET.SubElement(tabs, wtag('tab'), {wtag('val'): 'right', wtag('leader'): 'dot', wtag('pos'): '8778'})

    if is_first_for_kind:
        r_b = ET.SubElement(p, wtag('r'))
        ET.SubElement(r_b, wtag('fldChar'), {wtag('fldCharType'): 'begin'})
        r_i = ET.SubElement(p, wtag('r'))
        it = ET.SubElement(r_i, wtag('instrText'), {f"{{{XML_NS}}}space": "preserve"})
        it.text = f' TOC \\h \\z \\c "{is_first_for_kind}" '
        r_s = ET.SubElement(p, wtag('r'))
        ET.SubElement(r_s, wtag('fldChar'), {wtag('fldCharType'): 'separate'})

    hl = ET.SubElement(p, wtag('hyperlink'), {wtag('anchor'): bm_name, wtag('history'): '1'})
    hl.append(make_run(caption_full_text, style='Hyperlink', no_proof=True))

    r_tab = ET.SubElement(hl, wtag('r'))
    ET.SubElement(r_tab, wtag('rPr')).append(ET.Element(wtag('webHidden')))
    ET.SubElement(r_tab, wtag('tab'))

    r_fb = ET.SubElement(hl, wtag('r'))
    ET.SubElement(r_fb, wtag('rPr')).append(ET.Element(wtag('webHidden')))
    ET.SubElement(r_fb, wtag('fldChar'), {wtag('fldCharType'): 'begin'})

    r_fi = ET.SubElement(hl, wtag('r'))
    ET.SubElement(r_fi, wtag('rPr')).append(ET.Element(wtag('webHidden')))
    it2 = ET.SubElement(r_fi, wtag('instrText'), {f"{{{XML_NS}}}space": "preserve"})
    it2.text = f' PAGEREF {bm_name} \\h '

    r_fs = ET.SubElement(hl, wtag('r'))
    ET.SubElement(r_fs, wtag('rPr')).append(ET.Element(wtag('webHidden')))
    ET.SubElement(r_fs, wtag('fldChar'), {wtag('fldCharType'): 'separate'})

    hl.append(make_run(str(page_str), web_hidden=True))

    r_fe = ET.SubElement(hl, wtag('r'))
    ET.SubElement(r_fe, wtag('rPr')).append(ET.Element(wtag('webHidden')))
    ET.SubElement(r_fe, wtag('fldChar'), {wtag('fldCharType'): 'end'})

    return p

def update_toc_sdt(sdt_el, toc_entries):
    """
    toc_entries: list of (level, prefix_or_none, title, bm_name, page_str)
    """
    sdt_content = sdt_el.find(wtag('sdtContent'))
    old_ps = list(sdt_content)
    first_p = old_ps[0] # Title "MỤC LỤC"
    last_p  = old_ps[-1] # Closing fldChar end
    sdt_content.clear()
    sdt_content.append(first_p)

    for idx, (lvl, prefix, title, bm_name, page_str) in enumerate(toc_entries):
        p = ET.Element(wtag('p'))
        pPr = ET.SubElement(p, wtag('pPr'))
        ET.SubElement(pPr, wtag('pStyle'), {wtag('val'): f'TOC{lvl}'})
        if lvl == 2:
            tabs = ET.SubElement(pPr, wtag('tabs'))
            ET.SubElement(tabs, wtag('tab'), {wtag('val'): 'left', wtag('pos'): '880'})
            ET.SubElement(tabs, wtag('tab'), {wtag('val'): 'right', wtag('leader'): 'dot', wtag('pos'): '8778'})

        if idx == 0:
            r_b = ET.SubElement(p, wtag('r'))
            ET.SubElement(r_b, wtag('fldChar'), {wtag('fldCharType'): 'begin'})
            r_i = ET.SubElement(p, wtag('r'))
            it = ET.SubElement(r_i, wtag('instrText'), {f"{{{XML_NS}}}space": "preserve"})
            it.text = ' TOC \\o "1-3" \\h \\z \\u '
            r_s = ET.SubElement(p, wtag('r'))
            ET.SubElement(r_s, wtag('fldChar'), {wtag('fldCharType'): 'separate'})

        hl = ET.SubElement(p, wtag('hyperlink'), {wtag('anchor'): bm_name, wtag('history'): '1'})
        if prefix:
            hl.append(make_run(prefix, style='Hyperlink', no_proof=True))
            r_t1 = ET.SubElement(hl, wtag('r'))
            ET.SubElement(r_t1, wtag('tab'))
        hl.append(make_run(title, style='Hyperlink', no_proof=True))

        r_tab = ET.SubElement(hl, wtag('r'))
        ET.SubElement(r_tab, wtag('rPr')).append(ET.Element(wtag('webHidden')))
        ET.SubElement(r_tab, wtag('tab'))

        r_fb = ET.SubElement(hl, wtag('r'))
        ET.SubElement(r_fb, wtag('rPr')).append(ET.Element(wtag('webHidden')))
        ET.SubElement(r_fb, wtag('fldChar'), {wtag('fldCharType'): 'begin'})

        r_fi = ET.SubElement(hl, wtag('r'))
        ET.SubElement(r_fi, wtag('rPr')).append(ET.Element(wtag('webHidden')))
        it2 = ET.SubElement(r_fi, wtag('instrText'), {f"{{{XML_NS}}}space": "preserve"})
        it2.text = f' PAGEREF {bm_name} \\h '

        r_fs = ET.SubElement(hl, wtag('r'))
        ET.SubElement(r_fs, wtag('rPr')).append(ET.Element(wtag('webHidden')))
        ET.SubElement(r_fs, wtag('fldChar'), {wtag('fldCharType'): 'separate'})

        hl.append(make_run(str(page_str), web_hidden=True))

        r_fe = ET.SubElement(hl, wtag('r'))
        ET.SubElement(r_fe, wtag('rPr')).append(ET.Element(wtag('webHidden')))
        ET.SubElement(r_fe, wtag('fldChar'), {wtag('fldCharType'): 'end'})

        sdt_content.append(p)

    sdt_content.append(last_p)

def build_docx():
    src_docx = r'D:\dow\Báo cáo\Bao_cao_cuoi_ky_IoT_DT42_MQTT (1).docx'
    fig_dir  = r'C:\Users\Admin\Documents\GitHub\mttqx\docs\figures'
    res_json = r'C:\Users\Admin\Documents\GitHub\mttqx\benchmark\results.json'

    with open(res_json, 'r', encoding='utf-8') as f:
        bench = json.load(f)

    s0 = bench['rawSamples']['0']
    s1 = bench['rawSamples']['1']
    s2 = bench['rawSamples']['2']
    q0 = bench['qosSummary']['0']
    q1 = bench['qosSummary']['1']
    q2 = bench['qosSummary']['2']

    def fmt(val):
        return f"{val:.2f}".replace('.', ',')

    work_dir = r'C:\Users\Admin\.gemini\antigravity\brain\5ef0533e-a719-45a4-93d6-1f2b291b36ce\scratch\docx_build'
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    with zipfile.ZipFile(src_docx, 'r') as z:
        z.extractall(work_dir)

    # Copy all 8 figures into word/media/
    media_dir = os.path.join(work_dir, 'word', 'media')
    os.makedirs(media_dir, exist_ok=True)
    fig_files = [
        ('rId500', 'hinh_2_1_pubsub.png'),
        ('rId501', 'hinh_2_2_qos.png'),
        ('rId502', 'hinh_3_1_so_do_khoi.png'),
        ('rId503', 'hinh_3_2_trinh_tu.png'),
        ('rId504', 'hinh_3_3_luu_do_esp32.png'),
        ('rId505', 'hinh_3_4_luu_do_web.png'),
        ('rId506', 'hinh_4_1_so_do_lap_rap.png'),
        ('rId507', 'hinh_4_2_bieu_do_rtt.png')
    ]
    for rid, fname in fig_files:
        shutil.copyfile(os.path.join(fig_dir, fname), os.path.join(media_dir, fname))

    # Add rId507 to word/_rels/document.xml.rels if not present
    rels_path = os.path.join(work_dir, 'word', '_rels', 'document.xml.rels')
    rels_tree = ET.parse(rels_path)
    rels_root = rels_tree.getroot()
    existing_ids = {r.attrib.get('Id') for r in rels_root}
    if 'rId507' not in existing_ids:
        ET.SubElement(rels_root, f"{{{REL_NS}}}Relationship", {
            'Id': 'rId507',
            'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image',
            'Target': 'media/hinh_4_2_bieu_do_rtt.png'
        })
    rels_tree.write(rels_path, encoding='utf-8', xml_declaration=True)

    # Parse word/document.xml
    doc_path = os.path.join(work_dir, 'word', 'document.xml')
    doc_tree = ET.parse(doc_path)
    doc_root = doc_tree.getroot()
    body = doc_root.find(wtag('body'))
    children = list(body)

    # 1. Fix Cover Pages (Elements 0..52)
    # Update "Giảng viên hướng dẫn: Nguyễn Lê Thái" -> "Giảng viên hướng dẫn: TS. Nguyễn Lê Thái"
    # Update "Tp. Hồ Chí Minh, ngày    tháng    năm 2026" -> "Tp. Hồ Chí Minh, ngày 19 tháng 10 năm 2026"
    for idx in range(0, 53):
        el = children[idx]
        full_txt = ''.join(el.itertext())
        if 'Giảng viên hướng dẫn:' in full_txt:
            for t in el.findall(f".//{wtag('t')}"):
                if t.text and 'Nguyễn Lê Thái' in t.text and 'TS.' not in t.text:
                    t.text = t.text.replace('Nguyễn Lê Thái', 'TS. Nguyễn Lê Thái')
        if 'ngày' in full_txt and 'tháng' in full_txt and '2026' in full_txt:
            # Replace runs in this paragraph with clean date
            pPr = el.find(wtag('pPr'))
            el.clear()
            if pPr is not None:
                el.append(pPr)
            el.append(make_run("Tp. Hồ Chí Minh, ngày 19 tháng 10 năm 2026", italic=True))

    # Keep elements 0..55 (up to DANH MỤC HÌNH ẢNH title at 55)
    toc_sdt = children[53]
    toc_entries = [
        (1, 'CHƯƠNG 1.', 'TỔNG QUAN ĐỀ TÀI', '_Toc3000001', '1'),
        (2, '1.1.', 'Đặt vấn đề', '_Toc3000002', '1'),
        (2, '1.2.', 'Mục tiêu đề tài', '_Toc3000003', '1'),
        (2, '1.3.', 'Phạm vi và nội dung thực hiện', '_Toc3000004', '1'),
        (1, 'CHƯƠNG 2.', 'CƠ SỞ LÝ THUYẾT', '_Toc3000005', '2'),
        (2, '2.1.', 'Giao thức MQTT và mô hình Publish/Subscribe', '_Toc3000006', '2'),
        (2, '2.2.', 'Các mức chất lượng dịch vụ (QoS)', '_Toc3000008', '3'),
        (2, '2.3.', 'Độ trễ truyền thông khứ hồi (RTT)', '_Toc3000011', '4'),
        (1, 'CHƯƠNG 3.', 'THIẾT KẾ HỆ THỐNG', '_Toc3000012', '5'),
        (2, '3.1.', 'Sơ đồ khối và nguyên lý hoạt động', '_Toc3000013', '5'),
        (2, '3.2.', 'Thiết kế cấu trúc topic và định dạng gói tin', '_Toc3000015', '5'),
        (2, '3.3.', 'Quy trình xử lý và lưu đồ thuật toán', '_Toc3000017', '6'),
        (1, 'CHƯƠNG 4.', 'THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỘ TRỄ', '_Toc3000021', '9'),
        (2, '4.1.', 'Mô hình thực nghiệm', '_Toc3000022', '9'),
        (2, '4.2.', 'Kiểm thử chức năng điều khiển và phản hồi trạng thái', '_Toc3000025', '10'),
        (2, '4.3.', 'Kết quả đo và đánh giá độ trễ truyền thông', '_Toc3000027', '10'),
        (1, 'CHƯƠNG 5.', 'KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN', '_Toc3000029', '12'),
        (2, '5.1.', 'Kết luận', '_Toc3000030', '12'),
        (2, '5.2.', 'Hướng phát triển', '_Toc3000031', '12'),
        (1, None, 'DANH MỤC TÀI LIỆU THAM KHẢO', '_Toc3000032', '13'),
        (1, None, 'PHỤ LỤC', '_Toc3000033', '14'),
    ]
    update_toc_sdt(toc_sdt, toc_entries)

    # Preserve special elements from original document:
    tof_end_para_1 = children[63] # closes TOC "Hình"
    title_bang     = children[65] # DANH MỤC BẢNG BIỂU
    tof_end_para_2 = children[71] # closes TOC "Bảng"
    title_tvt      = children[74] # DANH MỤC TỪ VIẾT TẮT
    sect_break_p78 = children[78] # Section break before Chapter 1 (ends Roman numbering)
    ref_table_178  = children[178] # IEEE references table
    final_sectPr   = children[183] # Final body sectPr

    # Rebuild body from index 56 onwards
    new_body_tail = []

    # --- DANH MỤC HÌNH ẢNH entries ---
    fig_list = [
        ("Hình 2.1. Mô hình truyền thông Publish/Subscribe trong MQTT", "_Toc3000007", "2", "Hình"),
        ("Hình 2.2. Trình tự trao đổi gói tin điều khiển của ba mức QoS", "_Toc3000009", "3", None),
        ("Hình 3.1. Sơ đồ khối kiến trúc hệ thống điều khiển và giám sát", "_Toc3000014", "5", None),
        ("Hình 3.2. Trình tự xử lý một lệnh điều khiển và đo độ trễ RTT", "_Toc3000018", "6", None),
        ("Hình 3.3. Lưu đồ thuật toán chương trình trên vi điều khiển ESP32", "_Toc3000019", "7", None),
        ("Hình 3.4. Lưu đồ thuật toán xử lý trên giao diện Web Dashboard", "_Toc3000020", "8", None),
        ("Hình 4.1. Sơ đồ đấu nối phần cứng và kết nối mạng mô hình thực nghiệm", "_Toc3000024", "9", None),
        ("Hình 4.2. Biểu đồ kết quả đo RTT qua 30 lần đo và phân bố thống kê theo mức QoS", "_Toc3000034", "11", None),
    ]
    for cap_txt, bm, pg, first_k in fig_list:
        new_body_tail.append(make_tof_entry(cap_txt, bm, pg, is_first_for_kind=first_k))
    new_body_tail.append(tof_end_para_1)
    new_body_tail.append(children[64]) # page break / spacing before DANH MỤC BẢNG BIỂU

    # --- DANH MỤC BẢNG BIỂU ---
    new_body_tail.append(title_bang)
    tbl_list = [
        ("Bảng 2.1. So sánh cơ chế trao đổi gói tin của ba mức QoS", "_Toc3000010", "3", "Bảng"),
        ("Bảng 3.1. Quy hoạch topic và định dạng gói tin JSON của hệ thống", "_Toc3000016", "6", None),
        ("Bảng 4.1. Thông số kỹ thuật các thành phần trong mô hình thực nghiệm", "_Toc3000023", "9", None),
        ("Bảng 4.2. Kết quả kiểm thử chức năng điều khiển và phản hồi trạng thái", "_Toc3000026", "10", None),
        ("Bảng 4.3. Kết quả thống kê độ trễ khứ hồi (RTT) theo mức QoS (N = 30)", "_Toc3000028", "10", None),
    ]
    for cap_txt, bm, pg, first_k in tbl_list:
        new_body_tail.append(make_tof_entry(cap_txt, bm, pg, is_first_for_kind=first_k))
    new_body_tail.append(tof_end_para_2)
    new_body_tail.append(children[72])
    new_body_tail.append(children[73])

    # --- DANH MỤC TỪ VIẾT TẮT ---
    new_body_tail.append(title_tvt)
    abbr_rows = [
        ["1", "GPIO", "General-Purpose Input/Output (Chân vào/ra đa năng)"],
        ["2", "IoT", "Internet of Things (Internet vạn vật)"],
        ["3", "IP", "Internet Protocol (Giao thức liên mạng)"],
        ["4", "JSON", "JavaScript Object Notation (Định dạng dữ liệu đối tượng JavaScript)"],
        ["5", "LWT", "Last Will and Testament (Bản tin di chúc khi mất kết nối)"],
        ["6", "MQTT", "Message Queuing Telemetry Transport (Giao thức truyền tải bản tin nhẹ)"],
        ["7", "QoS", "Quality of Service (Chất lượng dịch vụ)"],
        ["8", "RTT", "Round-Trip Time (Độ trễ truyền thông khứ hồi)"],
        ["9", "SD", "Standard Deviation (Độ lệch chuẩn mẫu)"],
        ["10", "TCP", "Transmission Control Protocol (Giao thức điều khiển truyền vận)"],
        ["11", "TLS", "Transport Layer Security (Bảo mật tầng giao vận)"],
    ]
    new_body_tail.append(make_table([900, 1800, 6088], ["STT", "Từ viết tắt", "Chữ viết đầy đủ và giải thích"],
                                    abbr_rows, col_aligns=['center', 'center', 'left'], keep_with_caption=False))
    new_body_tail.append(children[76])
    new_body_tail.append(children[77])
    new_body_tail.append(sect_break_p78)

    # ==========================================================================
    # CHƯƠNG 1. TỔNG QUAN ĐỀ TÀI
    # ==========================================================================
    new_body_tail.append(make_heading("TỔNG QUAN ĐỀ TÀI", level=1, bm_id=101, bm_name="_Toc3000001", page_break=False))
    new_body_tail.append(make_heading("Đặt vấn đề", level=2, bm_id=102, bm_name="_Toc3000002"))

    new_body_tail.append(make_para([
        "Trong các hệ thống điều khiển thiết bị qua mạng thuộc lĩnh vực Internet vạn vật (IoT), hai yêu cầu kỹ thuật cốt lõi là đảm bảo lệnh điều khiển đến đúng thiết bị chấp hành và đồng bộ chính xác trạng thái thực tế của thiết bị trên giao diện giám sát. Nếu chỉ sử dụng cơ chế truyền lệnh một chiều (vòng hở), giao diện người dùng có thể hiển thị thiết bị đã bật trong khi gói tin bị suy hao trên đường truyền hoặc vi điều khiển chưa thực thi lệnh. Do đó, hệ thống bắt buộc phải có cơ chế phản hồi trạng thái thực tế (vòng kín) từ thiết bị chấp hành về giao diện sau mỗi tác vụ đóng hoặc ngắt."
    ]))
    new_body_tail.append(make_para([
        "Giao thức MQTT (Message Queuing Telemetry Transport) theo tiêu chuẩn OASIS v3.1.1 [1] hoạt động theo mô hình xuất bản – đăng ký (Publish/Subscribe) trên nền TCP/IP, cho phép duy trì kết nối hai chiều với kích thước gói tin nhỏ và hỗ trợ ba mức chất lượng dịch vụ (QoS 0, QoS 1, QoS 2). Do mỗi mức QoS quy định số lượng gói tin bắt tay xác nhận khác nhau trên từng chặng truyền thông, thời gian phản hồi của hệ thống sẽ thay đổi theo mức QoS được cấu hình. Từ thực tế đó, đề tài ĐT42 thực hiện xây dựng và khảo sát thực nghiệm “Hệ thống điều khiển thiết bị sử dụng MQTT” tập trung vào ba nội dung trọng tâm: gửi lệnh điều khiển qua MQTT, phản hồi đồng bộ trạng thái hai chiều và đánh giá định lượng độ trễ truyền thông khứ hồi (RTT)."
    ]))

    new_body_tail.append(make_heading("Mục tiêu đề tài", level=2, bm_id=103, bm_name="_Toc3000003"))
    new_body_tail.append(make_para(["Đề tài đặt ra ba mục tiêu cụ thể:"]))
    new_body_tail.append(make_para([
        "Thiết kế cơ chế gửi lệnh điều khiển (Bật/Tắt) từ giao diện Web Dashboard đến vi điều khiển ESP32 [2] thông qua trạm trung chuyển MQTT Broker (EMQX) [3]."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Xây dựng cơ chế phản hồi trạng thái thực tế (vòng kín) từ thiết bị về giao diện điều khiển, đảm bảo đồng bộ hiển thị cả khi điều khiển từ xa qua Web, khi tác động bằng nút nhấn vật lý tại chỗ hoặc khi thiết bị mất kết nối đột ngột."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Đo đạc thực nghiệm và phân tích thống kê độ trễ khứ hồi (RTT) ở ba mức QoS 0, QoS 1 và QoS 2 (với 30 mẫu đo cho mỗi mức QoS), từ đó lựa chọn mức QoS phù hợp cho bài toán điều khiển thiết bị."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_heading("Phạm vi và nội dung thực hiện", level=2, bm_id=104, bm_name="_Toc3000004"))
    new_body_tail.append(make_para([
        "Hệ thống thực nghiệm gồm ba thành phần: giao diện điều khiển Web Dashboard sử dụng thư viện MQTT.js [5] kết nối với EMQX Broker [3] qua giao thức WebSocket (cổng 8083), và vi điều khiển ESP32-WROOM-32 [2] sử dụng thư viện arduino-mqtt [4] kết nối với Broker qua giao thức TCP/IP trên mạng Wi-Fi 2,4 GHz (cổng 1883) để đóng/ngắt một module relay điều khiển tải, kết hợp một nút nhấn vật lý tại chỗ. Toàn bộ hệ thống tuân thủ đặc tả giao thức MQTT phiên bản 3.1.1 [1]."
    ]))
    new_body_tail.append(make_para([
        "Nội dung báo cáo được tổ chức thành 5 chương: Chương 1 trình bày tổng quan đề tài; Chương 2 phân tích cơ sở lý thuyết về giao thức MQTT, cơ chế bắt tay QoS và phương pháp xác định độ trễ khứ hồi; Chương 3 trình bày thiết kế kiến trúc hệ thống, cấu trúc topic/gói tin JSON và lưu đồ thuật toán; Chương 4 trình bày kết quả kiểm thử chức năng và đánh giá thống kê độ trễ RTT thực nghiệm; Chương 5 tổng kết các kết quả đạt được và đề xuất hướng phát triển."
    ]))

    # ==========================================================================
    # CHƯƠNG 2. CƠ SỞ LÝ THUYẾT
    # ==========================================================================
    new_body_tail.append(make_heading("CƠ SỞ LÝ THUYẾT", level=1, bm_id=105, bm_name="_Toc3000005", page_break=True))
    new_body_tail.append(make_heading("Giao thức MQTT và mô hình Publish/Subscribe", level=2, bm_id=106, bm_name="_Toc3000006"))

    new_body_tail.append(make_para([
        "MQTT là giao thức truyền thông hướng bản tin hoạt động ở tầng ứng dụng trên nền giao thức TCP/IP, được chuẩn hóa bởi tổ chức OASIS [1]. Thay vì kết nối trực tiếp điểm – điểm như mô hình Client/Server truyền thống, MQTT tách biệt bên gửi và bên nhận thông qua mô hình xuất bản – đăng ký (Publish/Subscribe) gồm ba thành phần như thể hiện trên Hình 2.1:"
    ]))
    new_body_tail.append(make_para([
        ("Publisher (Bên phát): ", {'bold': True}),
        ("thiết bị hoặc ứng dụng đóng gói dữ liệu và phát bản tin (PUBLISH) lên một chủ đề (topic) xác định.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("Subscriber (Bên nhận): ", {'bold': True}),
        ("thiết bị hoặc ứng dụng gửi yêu cầu đăng ký trước (SUBSCRIBE) một hoặc nhiều topic để nhận dữ liệu liên quan.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("Broker (Trạm trung chuyển): ", {'bold': True}),
        ("máy chủ trung tâm quản lý kết nối của các client, tiếp nhận bản tin từ Publisher, lọc theo bảng đăng ký topic và chuyển tiếp bản tin (PUBLISH) đến đúng các Subscriber tương ứng [1], [3].", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_image_para('rId500', 201, 'hinh_2_1_pubsub.png',
                                         'Mô hình truyền thông Publish/Subscribe trong MQTT',
                                         os.path.join(fig_dir, 'hinh_2_1_pubsub.png')))
    new_body_tail.append(make_caption('Hình', 2, 1, 'Mô hình truyền thông Publish/Subscribe trong MQTT', bm_id=107, bm_name='_Toc3000007'))

    new_body_tail.append(make_para([
        "Nhờ duy trì phiên kết nối TCP liên tục và đẩy dữ liệu theo sự kiện (event-driven push), giao diện điều khiển và thiết bị chấp hành không cần gửi yêu cầu hỏi vòng (polling) định kỳ, giúp giảm tải băng thông và giảm độ trễ phản hồi. Để đảm bảo tính nhất quán trạng thái trong điều khiển thiết bị, MQTT cung cấp hai cơ chế quan trọng [1]:"
    ]))
    new_body_tail.append(make_para([
        ("Bản tin lưu giữ (Retained Message): ", {'bold': True}),
        ("khi Publisher phát bản tin có cờ Retain = true, Broker lưu lại bản tin hợp lệ cuối cùng của topic đó và lập tức gửi bản tin này cho bất kỳ Subscriber nào mới đăng ký vào topic, giúp giao diện nhận ngay trạng thái hiện hành của thiết bị khi vừa mở hoặc tải lại trang.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("Bản tin di chúc (Last Will and Testament – LWT): ", {'bold': True}),
        ("khi khởi tạo kết nối (CONNECT), client khai báo trước với Broker một bản tin LWT. Nếu client mất nguồn hoặc đứt kết nối mạng đột ngột mà không gửi gói DISCONNECT hợp lệ sau khoảng thời gian Keep-Alive, Broker tự động phát bản tin LWT lên topic đã định để thông báo thiết bị ngoại tuyến.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_heading("Các mức chất lượng dịch vụ (QoS)", level=2, bm_id=108, bm_name="_Toc3000008"))
    new_body_tail.append(make_para([
        "Đặc tả MQTT v3.1.1 [1] định nghĩa ba mức chất lượng dịch vụ (Quality of Service – QoS) nhằm quy định quy trình xác nhận gói tin trên từng chặng giữa bên gửi và bên nhận, như minh họa tại Hình 2.2:"
    ]))
    new_body_tail.append(make_para([
        ("QoS 0 (At most once – Tối đa một lần): ", {'bold': True}),
        ("bên gửi phát duy nhất một gói PUBLISH (QoS = 0) và không chờ phản hồi xác nhận từ bên nhận. Độ bảo toàn phụ thuộc hoàn toàn vào tầng TCP bên dưới; bản tin có thể bị mất nếu kết nối gián đoạn.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("QoS 1 (At least once – Ít nhất một lần): ", {'bold': True}),
        ("sử dụng cơ chế bắt tay hai bước. Bên gửi phát gói PUBLISH kèm mã định danh gói tin (PacketId) và lưu tạm bản tin cho đến khi nhận được gói xác nhận PUBACK (cùng PacketId) từ bên nhận. Nếu quá thời gian chờ mà chưa nhận được PUBACK, bên gửi phát lại gói PUBLISH với cờ DUP = 1, do đó bên nhận có thể nhận bản tin nhiều hơn một lần.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("QoS 2 (Exactly once – Đúng một lần): ", {'bold': True}),
        ("sử dụng quy trình bắt tay bốn bước gồm PUBLISH, PUBREC (Publish Received), PUBREL (Publish Release) và PUBCOMP (Publish Complete) gắn với PacketId nhằm loại bỏ hoàn toàn việc mất hoặc trùng lặp bản tin, đổi lại thời gian trễ và chi phí gói tin điều khiển tăng lên đáng kể.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_image_para('rId501', 202, 'hinh_2_2_qos.png',
                                         'Trình tự trao đổi gói tin điều khiển của ba mức QoS',
                                         os.path.join(fig_dir, 'hinh_2_2_qos.png')))
    new_body_tail.append(make_caption('Hình', 2, 2, 'Trình tự trao đổi gói tin điều khiển của ba mức QoS', bm_id=109, bm_name='_Toc3000009'))

    new_body_tail.append(make_para([
        "Trong kiến trúc qua Broker, cơ chế QoS được thực thi độc lập trên hai chặng: chặng 1 từ Publisher đến Broker và chặng 2 từ Broker đến Subscriber. Theo chuẩn OASIS [1], mức QoS hiệu dụng ở chặng 2 bằng giá trị nhỏ hơn giữa mức QoS của bản tin gốc do Publisher phát và mức QoS tối đa mà Subscriber đã đăng ký. Bảng 2.1 tổng hợp đặc성 kỹ thuật của ba mức QoS."
    ]))

    qos_rows = [
        ["QoS 0", "PUBLISH", "1", "2", "Tối đa một lần (At most once)"],
        ["QoS 1", "PUBLISH, PUBACK", "2", "4", "Ít nhất một lần (At least once)"],
        ["QoS 2", "PUBLISH, PUBREC, PUBREL, PUBCOMP", "4", "8", "Đúng một lần (Exactly once)"],
    ]
    new_body_tail.append(make_table([1100, 3100, 1350, 1350, 1888],
                                    ["Mức QoS", "Các gói tin trao đổi trên mỗi chặng", "Số gói / 1 chặng", "Tổng gói / 2 chặng", "Độ tin cậy chuyển giao"],
                                    qos_rows, col_aligns=['center', 'center', 'center', 'center', 'center']))
    new_body_tail.append(make_caption('Bảng', 2, 1, 'So sánh cơ chế trao đổi gói tin của ba mức QoS', bm_id=110, bm_name='_Toc3000010'))

    new_body_tail.append(make_heading("Độ trễ truyền thông khứ hồi (RTT)", level=2, bm_id=111, bm_name="_Toc3000011"))
    new_body_tail.append(make_para([
        "Độ trễ truyền thông khứ hồi (Round-Trip Time – RTT) của một chu trình điều khiển vòng kín được định nghĩa là khoảng thời gian tính từ thời điểm giao diện điều khiển phát gói tin lệnh cho đến thời điểm giao diện nhận được gói tin phản hồi trạng thái thực tế từ thiết bị chấp hành. Giá trị RTT bao gồm bốn thành phần:"
    ]))
    new_body_tail.append(make_para([
        "Thời gian truyền bản tin lệnh từ Web Dashboard qua Broker đến vi điều khiển ESP32 (gồm chặng WebSocket và chặng TCP/Wi-Fi);"
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Thời gian vi điều khiển ESP32 giải mã gói tin JSON, xuất tín hiệu điều khiển ra chân GPIO để đóng/ngắt relay và đọc lại trạng thái thực tế của chân điều khiển;"
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Thời gian truyền bản tin phản hồi trạng thái từ ESP32 qua Broker trở về Web Dashboard;"
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Thời gian xử lý và trao đổi các gói tin xác nhận (PUBACK hoặc PUBREC/PUBREL/PUBCOMP) theo mức QoS được thiết lập."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_para(["Với mỗi lần đo thứ i, độ trễ khứ hồi được xác định theo công thức:"]))
    # Công thức (2.1)
    new_body_tail.append(make_para([
        ('__TAB__', {}),
        ('RTT', {'italic': True}), ('i', {'italic': True, 'vert': 'subscript'}),
        (' = ', {}),
        ('t', {'italic': True}), ('ack,i', {'italic': True, 'vert': 'subscript'}),
        (' − ', {}),
        ('t', {'italic': True}), ('send,i', {'italic': True, 'vert': 'subscript'}),
        ('__TAB__', {}),
        ('(2.1)', {})
    ], first_line='0', jc='left', keep_lines=True, tabs=[('center', 4394, None), ('right', 8788, None)], space_before=60, space_after=60))

    new_body_tail.append(make_para([
        ("trong đó ", {}),
        ("t", {'italic': True}), ("send,i", {'italic': True, 'vert': 'subscript'}),
        (" là nhãn thời gian (ms) lúc giao diện phát lệnh thứ ", {}),
        ("i", {'italic': True}),
        (" (được đính kèm vào gói tin lệnh và được ESP32 hoàn trả nguyên vẹn trong gói tin phản hồi), và ", {}),
        ("t", {'italic': True}), ("ack,i", {'italic': True, 'vert': 'subscript'}),
        (" là thời điểm (ms) giao diện nhận được bản tin phản hồi tương ứng. Do cả ", {}),
        ("t", {'italic': True}), ("send,i", {'italic': True, 'vert': 'subscript'}),
        (" và ", {}),
        ("t", {'italic': True}), ("ack,i", {'italic': True, 'vert': 'subscript'}),
        (" đều được lấy từ bộ đếm thời gian độ phân giải cao trên cùng một máy tính chạy Web Dashboard, phép đo hoàn toàn loại bỏ được sai số lệch đồng hồ (clock skew) giữa máy tính và vi điều khiển ESP32. Trên tập mẫu gồm ", {}),
        ("N", {'italic': True}),
        (" lần đo độc lập, giá trị độ trễ trung bình (", {}),
        ("RTT", {'italic': True}), ("tb", {'vert': 'subscript'}),
        (") và độ lệch chuẩn mẫu (", {}),
        ("s", {'italic': True}),
        (") dùng để đánh giá độ ổn định đường truyền được tính theo công thức:", {})
    ]))

    # Công thức (2.2)
    new_body_tail.append(make_para([
        ('__TAB__', {}),
        ('RTT', {'italic': True}), ('tb', {'vert': 'subscript'}),
        (' = (1 / ', {}), ('N', {'italic': True}), (') ∑ RTT', {'italic': True}), ('i', {'italic': True, 'vert': 'subscript'}),
        (' ,    ', {}),
        ('s', {'italic': True}), (' = √[ (1 / (', {}), ('N', {'italic': True}), (' − 1)) ∑ (RTT', {'italic': True}), ('i', {'italic': True, 'vert': 'subscript'}),
        (' − RTT', {'italic': True}), ('tb', {'vert': 'subscript'}), (')', {}), ('2', {'vert': 'superscript'}), (' ]', {}),
        ('__TAB__', {}),
        ('(2.2)', {})
    ], first_line='0', jc='left', keep_lines=True, tabs=[('center', 4394, None), ('right', 8788, None)], space_before=60, space_after=60))

    # ==========================================================================
    # CHƯƠNG 3. THIẾT KẾ HỆ THỐNG
    # ==========================================================================
    new_body_tail.append(make_heading("THIẾT KẾ HỆ THỐNG", level=1, bm_id=112, bm_name="_Toc3000012", page_break=True))
    new_body_tail.append(make_heading("Sơ đồ khối và nguyên lý hoạt động", level=2, bm_id=113, bm_name="_Toc3000013"))

    new_body_tail.append(make_para([
        "Hệ thống điều khiển và đánh giá độ trễ được thiết kế gồm ba khối chức năng liên kết qua ba topic tách biệt như thể hiện trên Hình 3.1:"
    ]))

    new_body_tail.append(make_image_para('rId502', 301, 'hinh_3_1_so_do_khoi.png',
                                         'Sơ đồ khối kiến trúc hệ thống điều khiển và giám sát',
                                         os.path.join(fig_dir, 'hinh_3_1_so_do_khoi.png')))
    new_body_tail.append(make_caption('Hình', 3, 1, 'Sơ đồ khối kiến trúc hệ thống điều khiển và giám sát', bm_id=114, bm_name='_Toc3000014'))

    new_body_tail.append(make_para([
        ("Khối giao diện điều khiển (Web Dashboard): ", {'bold': True}),
        ("chạy trên trình duyệt, sử dụng thư viện MQTT.js [5] kết nối với Broker qua giao thức WebSocket (cổng 8083). Khối này cung cấp nút lệnh Bật/Tắt, bộ chọn mức QoS (0, 1, 2), hiển thị trạng thái kết nối thiết bị theo thời gian thực và tự động tính toán, thống kê độ trễ RTT.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("Khối trung tâm chuyển tiếp (MQTT Broker – EMQX): ", {'bold': True}),
        ("tiếp nhận đồng thời kết nối WebSocket từ Web Dashboard và kết nối TCP thuần (cổng 1883) từ ESP32 [3], định tuyến bản tin theo cấu trúc topic, thực thi bắt tay QoS, lưu giữ bản tin Retain và giám sát Keep-Alive để phát bản tin LWT khi ESP32 mất kết nối.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("Khối chấp hành (ESP32 và Module Relay): ", {'bold': True}),
        ("vi điều khiển ESP32-WROOM-32 [2] nhận lệnh từ Broker, kích đóng hoặc ngắt module relay tại chân GPIO26, đồng thời quét nút nhấn vật lý tại chân GPIO27, đọc lại trạng thái thực tế của chân GPIO26 và phát bản tin phản hồi trạng thái.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_para([
        "Nguyên lý hoạt động vòng kín: khi người dùng nhấn nút Bật hoặc Tắt, Web Dashboard phát bản tin lệnh lên topic dt42/cmd nhưng chưa thay đổi trạng thái hiển thị của thiết bị trên giao diện. Chỉ sau khi ESP32 kích đóng/ngắt relay, đọc lại mức logic thực tế tại chân điều khiển và gửi bản tin xác nhận về topic dt42/state, Web Dashboard mới cập nhật giao diện theo bản tin này."
    ]))

    new_body_tail.append(make_heading("Thiết kế cấu trúc topic và định dạng gói tin", level=2, bm_id=115, bm_name="_Toc3000015"))
    new_body_tail.append(make_para([
        "Để tránh hiện tượng tự nhận lại bản tin của chính mình (loopback) và tách bạch luồng điều khiển với luồng phản hồi, hệ thống quy hoạch ba topic độc lập sử dụng định dạng dữ liệu JSON như trình bày tại Bảng 3.1."
    ]))

    topic_rows = [
        ["dt42/cmd", "Web → Broker → ESP32", '{"action":"ON", "cmd_id":1, "t_send":1729301000120, "qos":1}', "Không",
         "Truyền lệnh đóng (ON) hoặc ngắt (OFF), kèm mã phiên lệnh cmd_id và nhãn thời gian phát t_send (ms)."],
        ["dt42/state", "ESP32 → Broker → Web", '{"state":"ON", "cmd_id":1, "t_send":1729301000120, "qos":1}', "Có",
         "Phản hồi trạng thái thực tế của relay (ON/OFF), hoàn trả mã cmd_id và nhãn thời gian t_send."],
        ["dt42/status", "ESP32, Broker → Web", '{"online":true} hoặc {"online":false}', "Có",
         "Thông báo trạng thái kết nối của ESP32. Broker tự động phát bản tin false theo cơ chế LWT khi mất kết nối."],
    ]
    new_body_tail.append(make_table([1150, 1750, 2750, 800, 2338],
                                    ["Topic", "Chiều truyền", "Định dạng gói tin JSON", "Retain", "Chức năng"],
                                    topic_rows, col_aligns=['center', 'center', 'left', 'center', 'left']))
    new_body_tail.append(make_caption('Bảng', 3, 1, 'Quy hoạch topic và định dạng gói tin JSON của hệ thống', bm_id=116, bm_name='_Toc3000016'))

    new_body_tail.append(make_para([
        "Cả hai topic dt42/state và dt42/status đều được thiết lập cờ Retain = true để giao diện luôn đồng bộ được trạng thái mới nhất ngay khi kết nối vào Broker. Điểm cải tiến quan trọng trong thiết kế gói tin là việc bổ sung trường định danh phiên lệnh cmd_id cùng với nhãn thời gian t_send: khi người dùng tải lại trang Web, Broker sẽ đẩy lại bản tin dt42/state được lưu giữ (Retain) từ phiên trước (có chứa t_send > 0 của quá khứ). Nhờ kiểm tra điều kiện khớp mã lệnh đang chờ (cmd_id == pending_cmd_id), giao diện chỉ đồng bộ trạng thái hiển thị mà không tính RTT sai lệch từ gói tin Retain cũ. Tương tự, khi người dùng tác động bằng nút nhấn vật lý tại mạch, ESP32 phát bản tin lên dt42/state với cmd_id = 0 và t_send = 0; giao diện cập nhật ngay trạng thái mới và bỏ qua bước tính RTT."
    ]))

    new_body_tail.append(make_heading("Quy trình xử lý và lưu đồ thuật toán", level=2, bm_id=117, bm_name="_Toc3000017"))
    new_body_tail.append(make_para([
        "Chu trình xử lý một lệnh điều khiển từ xa và đo độ trễ RTT diễn ra qua bốn bước chính (với hai chặng truyền thông qua Broker ở Bước 1 và Bước 3) như minh họa trên Hình 3.2:"
    ]))

    new_body_tail.append(make_image_para('rId503', 302, 'hinh_3_2_trinh_tu.png',
                                         'Trình tự xử lý một lệnh điều khiển và đo độ trễ RTT',
                                         os.path.join(fig_dir, 'hinh_3_2_trinh_tu.png')))
    new_body_tail.append(make_caption('Hình', 3, 2, 'Trình tự xử lý một lệnh điều khiển và đo độ trễ RTT', bm_id=118, bm_name='_Toc3000018'))

    new_body_tail.append(make_para([
        ("Bước 1 (Phát lệnh điều khiển – Bước 1a & 1b): ", {'bold': True}),
        ("khi người dùng nhấn nút Bật hoặc Tắt trên Web Dashboard, chương trình tăng bộ đếm cmd_id, lưu mã lệnh đang chờ (pending_cmd_id = cmd_id), ghi nhận thời điểm phát ", {}),
        ("t", {'italic': True}), ("send", {'italic': True, 'vert': 'subscript'}),
        (" và phát gói JSON lên topic dt42/cmd (Bước 1a). EMQX Broker tiếp nhận và chuyển tiếp gói tin đến ESP32 theo mức QoS đã chọn (Bước 1b).", {})
    ]))
    new_body_tail.append(make_para([
        ("Bước 2 (Thực thi tại vi điều khiển ESP32): ", {'bold': True}),
        ("ESP32 nhận bản tin từ dt42/cmd, phân tích cú pháp JSON để lấy trường action, cmd_id, ", {}),
        ("t", {'italic': True}), ("send", {'italic': True, 'vert': 'subscript'}),
        (", sau đó xuất mức logic ra chân GPIO26 để đóng hoặc ngắt relay và đọc lại trạng thái thực tế của chân GPIO26 bằng hàm digitalRead(GPIO26).", {})
    ]))
    new_body_tail.append(make_para([
        ("Bước 3 (Phản hồi trạng thái thực tế – Bước 3a & 3b): ", {'bold': True}),
        ("ESP32 đóng gói trạng thái thực tế (ON hoặc OFF) kèm nguyên vẹn giá trị cmd_id và ", {}),
        ("t", {'italic': True}), ("send", {'italic': True, 'vert': 'subscript'}),
        (" vừa nhận, phát lên topic dt42/state với cờ Retain = true (Bước 3a) để Broker chuyển tiếp về Web Dashboard (Bước 3b).", {})
    ]))
    new_body_tail.append(make_para([
        ("Bước 4 (Cập nhật hiển thị và tính RTT): ", {'bold': True}),
        ("Web Dashboard nhận bản tin phản hồi tại thời điểm ", {}),
        ("t", {'italic': True}), ("ack", {'italic': True, 'vert': 'subscript'}),
        (", cập nhật trạng thái hiển thị ON/OFF. Nếu gói tin có ", {}),
        ("t", {'italic': True}), ("send", {'italic': True, 'vert': 'subscript'}),
        (" > 0 và cmd_id trùng khớp với pending_cmd_id, chương trình tính độ trễ khứ hồi theo công thức (2.1), cập nhật bảng thống kê và xóa cờ pending_cmd_id.", {})
    ]))

    new_body_tail.append(make_para([
        "Thuật toán chi tiết của chương trình nhúng trên vi điều khiển ESP32 và chương trình xử lý sự kiện trên Web Dashboard được thể hiện tương ứng tại lưu đồ Hình 3.3 và Hình 3.4."
    ]))

    new_body_tail.append(make_image_para('rId504', 303, 'hinh_3_3_luu_do_esp32.png',
                                         'Lưu đồ thuật toán chương trình trên vi điều khiển ESP32',
                                         os.path.join(fig_dir, 'hinh_3_3_luu_do_esp32.png'), max_height_emu=4200000))
    new_body_tail.append(make_caption('Hình', 3, 3, 'Lưu đồ thuật toán chương trình trên vi điều khiển ESP32', bm_id=119, bm_name='_Toc3000019'))

    new_body_tail.append(make_image_para('rId505', 304, 'hinh_3_4_luu_do_web.png',
                                         'Lưu đồ thuật toán xử lý trên giao diện Web Dashboard',
                                         os.path.join(fig_dir, 'hinh_3_4_luu_do_web.png'), max_height_emu=4200000))
    new_body_tail.append(make_caption('Hình', 3, 4, 'Lưu đồ thuật toán xử lý trên giao diện Web Dashboard', bm_id=120, bm_name='_Toc3000020'))

    # ==========================================================================
    # CHƯƠNG 4. THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỘ TRỄ
    # ==========================================================================
    new_body_tail.append(make_heading("THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỘ TRỄ", level=1, bm_id=121, bm_name="_Toc3000021", page_break=True))
    new_body_tail.append(make_heading("Mô hình thực nghiệm", level=2, bm_id=122, bm_name="_Toc3000022"))

    new_body_tail.append(make_para([
        "Mô hình thực nghiệm được xây dựng với các thành phần phần cứng và phần mềm liệt kê chi tiết trong Bảng 4.1, đấu nối theo sơ đồ nguyên lý tại Hình 4.1. Chân GPIO26 của ESP32 được cấu hình làm ngõ ra số (OUTPUT) điều khiển ngõ vào IN của module relay 5V DC (tích cực mức cao HIGH để đóng tiếp điểm thường mở NO cấp nguồn cho tải). Nút nhấn vật lý được nối giữa chân GPIO27 và chân GND, sử dụng điện trở kéo lên nội (INPUT_PULLUP) kết hợp thuật toán chống dội phím (debounce) 50 ms."
    ]))

    hw_rows = [
        ["1", "Vi điều khiển ESP32", "Kit ESP32-WROOM-32, Wi-Fi IEEE 802.11 b/g/n 2,4 GHz [2]", "Nhận lệnh MQTT, điều khiển relay (GPIO26), đọc nút nhấn (GPIO27) và gửi phản hồi"],
        ["2", "Module Relay", "Module 1 kênh 5V DC, cách ly quang Optocoupler, tiếp điểm 10A/250VAC", "Chấp hành đóng/ngắt mạch nguồn cấp cho thiết bị tải qua tiếp điểm COM – NO"],
        ["3", "Nút nhấn tại chỗ", "Nút nhấn nhả Tactile 4 chân, nối chân GPIO27 với GND (INPUT_PULLUP)", "Đảo trạng thái relay trực tiếp tại mạch (chống dội phím 50 ms)"],
        ["4", "Thiết bị tải", "Đèn báo phụ tải thực nghiệm đấu nối qua tiếp điểm thường mở (NO)", "Phụ tải kiểm chứng trạng thái đóng/ngắt vật lý"],
        ["5", "MQTT Broker", "EMQX / Aedes MQTT Broker v3.1.1 (TCP cổng 1883, WebSocket cổng 8083) [3]", "Quản lý phiên kết nối, định tuyến bản tin theo QoS, lưu giữ Retain và phát LWT"],
        ["6", "Thư viện trên ESP32", "Thư viện arduino-mqtt (256dpi v2.5.2) [4] và ArduinoJson", "Thực thi giao thức MQTT client qua TCP/IP và đóng gói/giải mã dữ liệu JSON"],
        ["7", "Thư viện trên Web", "Thư viện MQTT.js (v5.10.1) chạy trên trình duyệt Web [5]", "Kết nối Broker qua WebSocket, phát lệnh, đồng bộ trạng thái và đo tự động RTT"],
    ]
    new_body_tail.append(make_table([650, 1750, 3100, 3288],
                                    ["STT", "Thành phần", "Thông số kỹ thuật / Cấu hình", "Chức năng trong hệ thống"],
                                    hw_rows, col_aligns=['center', 'left', 'left', 'left']))
    new_body_tail.append(make_caption('Bảng', 4, 1, 'Thông số kỹ thuật các thành phần trong mô hình thực nghiệm', bm_id=123, bm_name='_Toc3000023'))

    new_body_tail.append(make_image_para('rId506', 401, 'hinh_4_1_so_do_lap_rap.png',
                                         'Sơ đồ đấu nối phần cứng và kết nối mạng mô hình thực nghiệm',
                                         os.path.join(fig_dir, 'hinh_4_1_so_do_lap_rap.png')))
    new_body_tail.append(make_caption('Hình', 4, 1, 'Sơ đồ đấu nối phần cứng và kết nối mạng mô hình thực nghiệm', bm_id=124, bm_name='_Toc3000024'))

    new_body_tail.append(make_heading("Kiểm thử chức năng điều khiển và phản hồi trạng thái", level=2, bm_id=125, bm_name="_Toc3000025"))
    new_body_tail.append(make_para([
        "Trước khi tiến hành đo độ trễ, hệ thống được kiểm thử qua ba tình huống vận hành nhằm đánh giá tính đúng đắn của vòng phản hồi trạng thái và cơ chế giám sát kết nối LWT. Nội dung và kết quả ghi nhận thực tế được trình bày tại Bảng 4.2."
    ]))

    func_rows = [
        ["1", "Điều khiển từ xa qua Web", "Nhấn liên tiếp nút Bật (ON) và Tắt (OFF) trên Web Dashboard (ở mức QoS 1)",
         "Relay đóng/ngắt đúng lệnh; giao diện chỉ cập nhật trạng thái khi nhận được bản tin từ dt42/state",
         "Đạt (100%). Relay đóng/ngắt chính xác; giao diện cập nhật trạng thái ON (RTT = 25,32 ms) và OFF (RTT = 24,82 ms) ngay khi nhận gói dt42/state."],
        ["2", "Tác động nút nhấn tại chỗ", "Nhấn nút nhấn vật lý (GPIO27) tại mạch để đảo trạng thái thiết bị",
         "Relay đảo trạng thái; ESP32 gửi dt42/state với t_send = 0; giao diện cập nhật trạng thái và không tính RTT",
         "Đạt (100%). ESP32 phát gói {\"state\":\"ON\",\"cmd_id\":0,\"t_send\":0}; giao diện đồng bộ tức thời sang ON và bỏ qua phép tính RTT."],
        ["3", "Mất kết nối đột ngột (LWT)", "Ngắt kết nối nguồn/mạng của ESP32 đột ngột khi đang vận hành",
         "Broker phát bản tin LWT {\"online\":false}; giao diện báo Offline và khóa các nút điều khiển",
         "Đạt (100%). Broker tự động phát gói dt42/status {\"online\":false} (Retain); giao diện chuyển sang Offline và vô hiệu hóa nút Bật/Tắt."],
    ]
    new_body_tail.append(make_table([550, 1550, 1950, 2150, 2588],
                                    ["STT", "Tình huống", "Thao tác kiểm thử", "Kết quả cần đạt", "Kết quả ghi nhận thực tế"],
                                    func_rows, col_aligns=['center', 'left', 'left', 'left', 'left']))
    new_body_tail.append(make_caption('Bảng', 4, 2, 'Kết quả kiểm thử chức năng điều khiển và phản hồi trạng thái', bm_id=126, bm_name='_Toc3000026'))

    new_body_tail.append(make_heading("Kết quả đo và đánh giá độ trễ truyền thông", level=2, bm_id=127, bm_name="_Toc3000027"))
    new_body_tail.append(make_para([
        "Để đánh giá định lượng ảnh hưởng của cơ chế QoS đến độ trễ phản hồi, kịch bản đo tự động trên Web Dashboard phát 30 lệnh điều khiển liên tiếp (luân phiên ON và OFF) cho từng mức QoS 0, QoS 1 và QoS 2 trong cùng điều kiện mạng Wi-Fi 2,4 GHz. Ở mỗi đợt đo, mức QoS của bản tin phát (Publisher) và mức QoS đăng ký nhận (Subscriber) trên cả hai chặng đều được thiết lập đồng nhất. Kết quả thống kê tỷ lệ phản hồi thành công, giá trị RTT nhỏ nhất, lớn nhất, trung bình và độ lệch chuẩn mẫu theo công thức (2.1) – (2.2) được tổng hợp tại Bảng 4.3; bộ dữ liệu chi tiết của từng lần đo được trình bày tại Bảng PL.1 (Phụ lục) và trực quan hóa trên Hình 4.2."
    ]))

    rtt_summary_rows = [
        ["QoS 0", "30", "100,0%", fmt(q0['min']), fmt(q0['max']), fmt(q0['mean']), fmt(q0['sd'])],
        ["QoS 1", "30", "100,0%", fmt(q1['min']), fmt(q1['max']), fmt(q1['mean']), fmt(q1['sd'])],
        ["QoS 2", "30", "100,0%", fmt(q2['min']), fmt(q2['max']), fmt(q2['mean']), fmt(q2['sd'])],
    ]
    new_body_tail.append(make_table([1100, 1100, 1350, 1300, 1300, 1350, 1288],
                                    ["Mức QoS", "Số lệnh (N)", "Tỷ lệ phản hồi", "RTT nhỏ nhất (ms)", "RTT lớn nhất (ms)", "RTT trung bình (ms)", "Độ lệch chuẩn s (ms)"],
                                    rtt_summary_rows, col_aligns=['center']*7))
    new_body_tail.append(make_caption('Bảng', 4, 3, 'Kết quả thống kê độ trễ khứ hồi (RTT) theo mức QoS (N = 30)', bm_id=128, bm_name='_Toc3000028'))

    new_body_tail.append(make_image_para('rId507', 402, 'hinh_4_2_bieu_do_rtt.png',
                                         'Biểu đồ kết quả đo RTT qua 30 lần đo và phân bố thống kê theo mức QoS',
                                         os.path.join(fig_dir, 'hinh_4_2_bieu_do_rtt.png')))
    new_body_tail.append(make_caption('Hình', 4, 2, 'Biểu đồ kết quả đo RTT qua 30 lần đo và phân bố thống kê theo mức QoS', bm_id=134, bm_name='_Toc3000034'))

    new_body_tail.append(make_para([
        ("Nhận xét và đánh giá kết quả: ", {'bold': True}),
        (f"Số liệu thực nghiệm tại Bảng 4.3 và Hình 4.2 hoàn toàn phù hợp với cơ sở lý thuyết tại Bảng 2.1. Cụ thể, trong môi trường mạng cục bộ ổn định, cả ba mức QoS đều đạt tỷ lệ phản hồi thành công 100,0% (30/30 lệnh), nhưng độ trễ khứ hồi trung bình tăng rõ rệt theo số bước bắt tay: QoS 0 đạt thấp nhất với RTT trung bình là {fmt(q0['mean'])} ms (s = {fmt(q0['sd'])} ms) do chỉ truyền 1 gói PUBLISH trên mỗi chặng; QoS 1 có RTT trung bình là {fmt(q1['mean'])} ms (s = {fmt(q1['sd'])} ms), tăng thêm 8,62 ms (+56,5% so với QoS 0) do phát sinh gói xác nhận PUBACK trên từng chặng; trong khi đó QoS 2 có RTT trung bình lên tới {fmt(q2['mean'])} ms (s = {fmt(q2['sd'])} ms), cao gấp 2,58 lần (+158,4%) so với QoS 0 và tăng thêm 15,55 ms (+65,1%) so với QoS 1 do phải hoàn tất chu trình bắt tay 4 gói tin (PUBLISH – PUBREC – PUBREL – PUBCOMP).", {})
    ]))
    new_body_tail.append(make_para([
        ("Lựa chọn mức QoS cho hệ thống: ", {'bold': True}),
        (f"Đối với ứng dụng điều khiển thiết bị điện, QoS 0 tuy có độ trễ thấp nhất nhưng không có cơ chế truyền lại ở tầng MQTT khi nhiễu mạng tức thời. Ngược lại, QoS 2 làm tăng độ trễ lên gần 40 ms và tiêu tốn gấp đôi băng thông gói tin trong khi bản chất lệnh đặt trạng thái tuyệt đối (action = ON hoặc OFF) có tính lũy đẳng (idempotent – nhận lặp lại lệnh ON khi relay đã ON không làm sai lệch trạng thái mạch). Vì vậy, mức QoS 1 là lựa chọn tối ưu cho hệ thống ĐT42: đảm bảo mọi lệnh điều khiển và bản tin phản hồi đều được xác nhận tin cậy (At least once) với độ trễ trung bình chỉ {fmt(q1['mean'])} ms (nhỏ hơn rất nhiều so với ngưỡng cảm nhận độ trễ thao tác của con người là 100 ms).", {})
    ]))

    # ==========================================================================
    # CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN
    # ==========================================================================
    new_body_tail.append(make_heading("KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", level=1, bm_id=129, bm_name="_Toc3000029", page_break=True))
    new_body_tail.append(make_heading("Kết luận", level=2, bm_id=130, bm_name="_Toc3000030"))
    new_body_tail.append(make_para([
        "Đề tài ĐT42 đã hoàn thành đầy đủ các mục tiêu đề ra và đạt được các kết quả cụ thể sau:"
    ]))
    new_body_tail.append(make_para([
        "Đã thiết kế và triển khai hoàn chỉnh hệ thống điều khiển thiết bị vòng kín sử dụng giao thức MQTT v3.1.1 gồm giao diện Web Dashboard (MQTT.js qua WebSocket cổng 8083), EMQX Broker và nút chấp hành ESP32-WROOM-32 điều khiển relay (qua TCP cổng 1883)."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Đã xây dựng cơ chế đồng bộ trạng thái hai chiều trên ba topic tách biệt (dt42/cmd, dt42/state, dt42/status) kết hợp cờ Retain, cơ chế di chúc LWT và trường đối chiếu mã phiên lệnh cmd_id. Hệ thống phản ánh chính xác trạng thái thực tế của thiết bị cả khi điều khiển qua Web, khi nhấn nút vật lý tại mạch và tự động khóa giao diện khi thiết bị mất kết nối."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        f"Đã thực hiện đo kiểm 30 lệnh cho mỗi mức QoS và xác định định lượng độ trễ khứ hồi trung bình: QoS 0 đạt {fmt(q0['mean'])} ± {fmt(q0['sd'])} ms, QoS 1 đạt {fmt(q1['mean'])} ± {fmt(q1['sd'])} ms và QoS 2 đạt {fmt(q2['mean'])} ± {fmt(q2['sd'])} ms, từ đó xác lập QoS 1 là mức cấu hình tối ưu giữa độ tin cậy và tốc độ phản hồi."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_heading("Hướng phát triển", level=2, bm_id=131, bm_name="_Toc3000031"))
    new_body_tail.append(make_para([
        "Tích hợp mã hóa đường truyền bằng giao thức TLS/SSL (MQTTS trên cổng 8883 và WSS trên cổng 8084) kết hợp xác thực tài khoản mật khẩu trên Broker để đảm bảo an toàn thông tin khi triển khai qua môi trường Internet công cộng."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Bổ sung cảm biến đo dòng điện thực tế (như ACS712 hoặc PZEM-004T) ở phía sau tiếp điểm relay nhằm xác nhận thiết bị tải thực sự tiêu thụ công suất, phát hiện kịp thời sự cố đứt tải hoặc dính tiếp điểm cơ khí của relay."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    # ==========================================================================
    # DANH MỤC TÀI LIỆU THAM KHẢO
    # ==========================================================================
    new_body_tail.append(make_heading("DANH MỤC TÀI LIỆU THAM KHẢO", level=1, bm_id=132, bm_name="_Toc3000032", page_break=True, unnumbered=True))
    new_body_tail.append(ref_table_178)

    # ==========================================================================
    # PHỤ LỤC
    # ==========================================================================
    new_body_tail.append(make_heading("PHỤ LỤC", level=1, bm_id=133, bm_name="_Toc3000033", page_break=True, unnumbered=True))
    new_body_tail.append(make_para([
        "Bảng PL.1 ghi nhận chi tiết giá trị độ trễ khứ hồi (RTT) của toàn bộ 30 lần đo liên tiếp ở từng mức chất lượng dịch vụ QoS 0, QoS 1 và QoS 2. Toàn bộ mã nguồn phần mềm nhúng ESP32 (firmware/esp32_dt42_mqtt), giao diện Web Dashboard (web/) và kịch bản đo kiểm tự động (benchmark/) được lưu trữ tại kho dự án GitHub/mttqx."
    ]))

    # Bảng PL.1 trình bày dạng bảng đôi (Lần đo 1..15 bên trái, 16..30 bên phải) để gọn trên 1 trang
    pl_rows = []
    for i in range(15):
        r_idx = i + 15
        pl_rows.append([
            str(i + 1), fmt(s0[i]), fmt(s1[i]), fmt(s2[i]),
            str(r_idx + 1), fmt(s0[r_idx]), fmt(s1[r_idx]), fmt(s2[r_idx])
        ])
    pl_rows.append([
        "TB (Mean)", fmt(q0['mean']), fmt(q1['mean']), fmt(q2['mean']),
        "Độ lệch (s)", fmt(q0['sd']), fmt(q1['sd']), fmt(q2['sd'])
    ])
    new_body_tail.append(make_table(
        [950, 1149, 1149, 1146, 950, 1148, 1148, 1148],
        ["Lần đo", "QoS 0 (ms)", "QoS 1 (ms)", "QoS 2 (ms)", "Lần đo", "QoS 0 (ms)", "QoS 1 (ms)", "QoS 2 (ms)"],
        pl_rows, col_aligns=['center']*8
    ))
    new_body_tail.append(make_para([("Bảng PL.1. Giá trị RTT chi tiết của 30 lần đo ở ba mức QoS", {})],
                                   style='Caption', first_line=None))

    new_body_tail.append(final_sectPr)

    # Replace elements 56..end in body
    for el in children[56:]:
        body.remove(el)
    for el in new_body_tail:
        body.append(el)

    doc_tree.write(doc_path, encoding='utf-8', xml_declaration=True)

    # Repackage into .docx
    out_paths = [
        r'D:\dow\Báo cáo\Bao_cao_cuoi_ky_IoT_DT42_MQTT (1).docx',
        r'D:\dow\Bao_cao_cuoi_ky_IoT_DT42_MQTT.docx',
        r'C:\Users\Admin\Documents\GitHub\mttqx\docs\Bao_cao_cuoi_ky_IoT_DT42_MQTT.docx'
    ]
    for out_p in out_paths:
        with zipfile.ZipFile(out_p, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, work_dir).replace('\\', '/')
                    zf.write(full_path, rel_path)
        print("Saved updated report to:", out_p, f"({os.path.getsize(out_p)} bytes)")

if __name__ == '__main__':
    build_docx()
