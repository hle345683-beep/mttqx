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

def make_run(text, bold=False, italic=False, vert=None, style=None, no_proof=False, web_hidden=False, sz=None):
    r = ET.Element(wtag('r'))
    if any([bold, italic, vert, style, no_proof, web_hidden, sz]):
        rPr = ET.SubElement(r, wtag('rPr'))
        if style:
            ET.SubElement(rPr, wtag('rStyle'), {wtag('val'): style})
        if bold:
            ET.SubElement(rPr, wtag('b'))
            ET.SubElement(rPr, wtag('bCs'))
        if italic:
            ET.SubElement(rPr, wtag('i'))
            ET.SubElement(rPr, wtag('iCs'))
        if no_proof:
            ET.SubElement(rPr, wtag('noProof'))
        if web_hidden:
            ET.SubElement(rPr, wtag('webHidden'))
        if sz:
            ET.SubElement(rPr, wtag('sz'), {wtag('val'): str(sz)})
            ET.SubElement(rPr, wtag('szCs'), {wtag('val'): str(sz)})
        if vert:
            ET.SubElement(rPr, wtag('vertAlign'), {wtag('val'): vert})
    t = ET.SubElement(r, wtag('t'))
    if text.startswith(' ') or text.endswith(' '):
        t.set(f"{{{XML_NS}}}space", "preserve")
    t.text = text
    return r

def make_para(runs_spec=None, style=None, jc=None, first_line='720', left=None, hanging=None,
              num_id=None, ilvl='0', page_break=False, keep_next=False, keep_lines=False,
              bm_id=None, bm_name=None, tabs=None, space_before=None, space_after=None,
              line_spacing=None, snap_to_grid=True, outline_lvl=None):
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
    if not snap_to_grid:
        ET.SubElement(pPr, wtag('snapToGrid'), {wtag('val'): '0'})
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
    if any(x is not None for x in [space_before, space_after, line_spacing]):
        sp_attr = {}
        if space_before is not None:
            sp_attr[wtag('before')] = str(space_before)
        if space_after is not None:
            sp_attr[wtag('after')] = str(space_after)
        if line_spacing is not None:
            sp_attr[wtag('line')] = str(line_spacing)
            sp_attr[wtag('lineRule')] = 'auto'
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
    if outline_lvl is not None:
        ET.SubElement(pPr, wtag('outlineLvl'), {wtag('val'): str(outline_lvl)})

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
            # Do NOT use Heading1 or numPr so viewers never attach a bullet/dash
            return make_para([(text, {'bold': True, 'sz': 32})], style=None, jc='center',
                             first_line='0', left='0', page_break=page_break,
                             keep_next=True, keep_lines=True, space_before=240, space_after=480,
                             outline_lvl=0, bm_id=bm_id, bm_name=bm_name)
        return make_para([text], style='Heading1', jc='center', first_line=None,
                         page_break=page_break, bm_id=bm_id, bm_name=bm_name)
    elif level == 2:
        return make_para([text], style='Heading2', first_line=None, keep_next=True, bm_id=bm_id, bm_name=bm_name)
    else:
        return make_para([text], style='Heading3', first_line=None, keep_next=True, bm_id=bm_id, bm_name=bm_name)

def make_caption(kind, chap_num, seq_num, title_text, bm_id=None, bm_name=None):
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

def make_image_para(rid, doc_id, filename, descr, img_path, target_cx=5486400, max_cy=4200000):
    with Image.open(img_path) as im:
        w_px, h_px = im.size
    aspect = h_px / float(w_px)
    cx = target_cx
    cy = int(cx * aspect)
    if cy > max_cy:
        cy = max_cy
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

def make_table(col_widths, headers, rows, col_aligns=None, keep_with_caption=True, cell_pad=40):
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
        p = make_para([(h_text, {'bold': True})], first_line='0', jc='center', keep_next=True,
                      space_before=cell_pad, space_after=cell_pad, line_spacing=240, snap_to_grid=False)
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
            p = make_para(runs, first_line='0', jc=align, keep_next=(is_last and keep_with_caption),
                          space_before=cell_pad, space_after=cell_pad, line_spacing=240, snap_to_grid=False)
            tc.append(p)

    return tbl

def make_tof_entry(caption_full_text, bm_name, page_str, is_first_for_kind=None):
    p = ET.Element(wtag('p'))
    pPr = ET.SubElement(p, wtag('pPr'))
    ET.SubElement(pPr, wtag('pStyle'), {wtag('val'): 'TableofFigures'})
    ET.SubElement(pPr, wtag('snapToGrid'), {wtag('val'): '0'})
    tabs = ET.SubElement(pPr, wtag('tabs'))
    ET.SubElement(tabs, wtag('tab'), {wtag('val'): 'right', wtag('leader'): 'dot', wtag('pos'): '8700'})
    ET.SubElement(pPr, wtag('spacing'), {wtag('before'): '0', wtag('after'): '60', wtag('line'): '240', wtag('lineRule'): 'auto'})

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
        ET.SubElement(pPr, wtag('snapToGrid'), {wtag('val'): '0'})
        tabs = ET.SubElement(pPr, wtag('tabs'))
        if lvl == 1:
            if prefix:
                ET.SubElement(tabs, wtag('tab'), {wtag('val'): 'left', wtag('pos'): '1760'})
            else:
                ET.SubElement(tabs, wtag('tab'), {wtag('val'): 'clear', wtag('pos'): '1760'})
            ET.SubElement(tabs, wtag('tab'), {wtag('val'): 'right', wtag('leader'): 'dot', wtag('pos'): '8700'})
        elif lvl == 2:
            ET.SubElement(tabs, wtag('tab'), {wtag('val'): 'left', wtag('pos'): '880'})
            ET.SubElement(tabs, wtag('tab'), {wtag('val'): 'right', wtag('leader'): 'dot', wtag('pos'): '8700'})
        ET.SubElement(pPr, wtag('spacing'), {wtag('before'): '0', wtag('after'): '45', wtag('line'): '240', wtag('lineRule'): 'auto'})

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
    # Use the clean Microsoft Word base (untouched by WPS styleId renumbering)
    orig_repo_docx = r'C:\Users\Admin\Documents\GitHub\mttqx\docs\Bao_cao_cuoi_ky_IoT_DT42_MQTT.docx'
    base_docx = r'C:\Users\Admin\.gemini\antigravity\brain\5ef0533e-a719-45a4-93d6-1f2b291b36ce\scratch\base_word_clean.docx'
    if not os.path.exists(base_docx):
        shutil.copyfile(orig_repo_docx, base_docx)
    orig_fig_dir = r'C:\Users\Admin\.gemini\antigravity\brain\5ef0533e-a719-45a4-93d6-1f2b291b36ce\scratch\baocao_media\word\media'
    repo_fig_dir = r'C:\Users\Admin\Documents\GitHub\mttqx\docs\figures'
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

    work_dir = r'C:\Users\Admin\.gemini\antigravity\brain\5ef0533e-a719-45a4-93d6-1f2b291b36ce\scratch\docx_clean_build'
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    with zipfile.ZipFile(base_docx, 'r') as z:
        z.extractall(work_dir)

    # Copy the 7 clean original figures into word/media/ and docs/figures/
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
    ]
    for rid, fname in fig_files:
        src_f = os.path.join(orig_fig_dir, fname)
        shutil.copyfile(src_f, os.path.join(media_dir, fname))
        shutil.copyfile(src_f, os.path.join(repo_fig_dir, fname))

    # Remove unused hinh_4_2_bieu_do_rtt.png from media_dir and document.xml.rels
    extra_fig = os.path.join(media_dir, 'hinh_4_2_bieu_do_rtt.png')
    if os.path.exists(extra_fig):
        os.remove(extra_fig)

    rels_path = os.path.join(work_dir, 'word', '_rels', 'document.xml.rels')
    rels_tree = ET.parse(rels_path)
    rels_root = rels_tree.getroot()
    for r in list(rels_root):
        if r.attrib.get('Id') == 'rId507':
            rels_root.remove(r)
    rels_tree.write(rels_path, encoding='utf-8', xml_declaration=True)

    # Remove stray cached 'v' and '8' in footer3.xml and footer4.xml so viewers don't show 'v' at end of file
    for ftr_name in ['footer3.xml', 'footer4.xml']:
        ftr_path = os.path.join(work_dir, 'word', ftr_name)
        if os.path.exists(ftr_path):
            ftr_txt = open(ftr_path, 'r', encoding='utf-8').read()
            ftr_txt = ftr_txt.replace('<w:t>v</w:t>', '<w:t></w:t>').replace('<w:t>8</w:t>', '<w:t></w:t>')
            open(ftr_path, 'w', encoding='utf-8').write(ftr_txt)

    # Parse word/document.xml
    doc_path = os.path.join(work_dir, 'word', 'document.xml')
    doc_tree = ET.parse(doc_path)
    doc_root = doc_tree.getroot()
    body = doc_root.find(wtag('body'))
    children = list(body)

    # 1. Fix Cover Pages (Elements 0..52)
    # - Keep "Giảng viên hướng dẫn: Nguyễn Lê Thái" as in user's original cover
    # - Fix topic title [7] and [25]: set sz="30" (15pt) so "HỆ THỐNG ĐIỀU KHIỂN THIẾT BỊ SỬ DỤNG MQTT" stays on 1 line
    # - Fix cover borders in [17] and split Section 2 right after [34] so both Cover 1 and Cover 2 have unconditional frame borders and Table 35 starts cleanly on Page 3 without a border
    for idx in range(0, 53):
        el = children[idx]
        full_txt = ''.join(el.itertext())
        if 'Giảng viên hướng dẫn:' in full_txt:
            for t in el.findall(f".//{wtag('t')}"):
                if t.text and 'TS. Nguyễn Lê Thái' in t.text:
                    t.text = t.text.replace('TS. Nguyễn Lê Thái', 'Nguyễn Lê Thái')
        if 'HỆ THỐNG ĐIỀU KHIỂN THIẾT BỊ SỬ DỤNG MQTT' in full_txt:
            for sz_el in el.findall(f".//{wtag('sz')}") + el.findall(f".//{wtag('szCs')}"):
                sz_el.set(wtag('val'), '30')

    # Make sure Cover 1 ([17]) and Cover 2 ([34]) have unconditional pgBorders (remove w:display="firstPage" and add <w:titlePg/> so WPS/Word always render the frame on the 1-page cover section)
    for sec_idx in [17, 39]:
        sect = children[sec_idx].find(f".//{wtag('sectPr')}")
        if sect is not None:
            pgb = sect.find(wtag('pgBorders'))
            if pgb is not None:
                if wtag('display') in pgb.attrib:
                    del pgb.attrib[wtag('display')]
                pgb.set(wtag('offsetFrom'), 'text')
                for side in pgb:
                    side.set(wtag('color'), '000000')

    # Now split Section 2 right after [34] ("TP.Hồ Chí Minh, tháng 10 / 2026"):
    # Put a copy of [17]'s sectPr on [34], and remove pgBorders from [39] (which ends Page 3 with Table 35 & 37)
    sect_cover1 = children[17].find(f".//{wtag('sectPr')}")
    sect_cover2_copy = ET.fromstring(ET.tostring(sect_cover1, encoding='unicode'))
    p34_pPr = children[34].find(wtag('pPr'))
    if p34_pPr.find(wtag('sectPr')) is None:
        p34_pPr.append(sect_cover2_copy)

    # Remove pgBorders from [39] so Page 3 (Table 35 & Table 37) has NO cover frame border
    sect_p39 = children[39].find(f".//{wtag('sectPr')}")
    if sect_p39 is not None:
        pgb39 = sect_p39.find(wtag('pgBorders'))
        if pgb39 is not None:
            sect_p39.remove(pgb39)

    # Update TOC ([53])
    toc_sdt = children[53]
    toc_entries = [
        (1, 'CHƯƠNG 1.', 'TỔNG QUAN ĐỀ TÀI', '_Toc3000001', '1'),
        (2, '1.1.', 'Đặt vấn đề', '_Toc3000002', '1'),
        (2, '1.2.', 'Mục tiêu đề tài', '_Toc3000003', '1'),
        (2, '1.3.', 'Phạm vi và nội dung thực hiện', '_Toc3000004', '1'),
        (1, 'CHƯƠNG 2.', 'CƠ SỞ LÝ THUYẾT', '_Toc3000005', '2'),
        (2, '2.1.', 'Giao thức MQTT và mô hình Publish/Subscribe', '_Toc3000006', '2'),
        (2, '2.2.', 'Các mức chất lượng dịch vụ (QoS)', '_Toc3000008', '3'),
        (2, '2.3.', 'Độ trễ truyền thông', '_Toc3000011', '4'),
        (1, 'CHƯƠNG 3.', 'THIẾT KẾ HỆ THỐNG', '_Toc3000012', '5'),
        (2, '3.1.', 'Sơ đồ khối và nguyên lý hoạt động', '_Toc3000013', '5'),
        (2, '3.2.', 'Thiết kế topic và gói tin', '_Toc3000015', '6'),
        (2, '3.3.', 'Quy trình xử lý và lưu đồ thuật toán', '_Toc3000017', '6'),
        (1, 'CHƯƠNG 4.', 'THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỘ TRỄ', '_Toc3000021', '9'),
        (2, '4.1.', 'Mô hình thực nghiệm', '_Toc3000022', '9'),
        (2, '4.2.', 'Kiểm thử chức năng', '_Toc3000025', '10'),
        (2, '4.3.', 'Đo độ trễ truyền thông', '_Toc3000027', '10'),
        (1, 'CHƯƠNG 5.', 'KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN', '_Toc3000029', '11'),
        (2, '5.1.', 'Kết luận', '_Toc3000030', '11'),
        (2, '5.2.', 'Hướng phát triển', '_Toc3000031', '11'),
        (1, None, 'DANH MỤC TÀI LIỆU THAM KHẢO', '_Toc3000032', '12'),
        (1, None, 'PHỤ LỤC', '_Toc3000033', '13'),
    ]
    update_toc_sdt(toc_sdt, toc_entries)

    # Locate preserved elements in base_docx (note indices in base_docx have +1 after 63 because base_docx had 8 figures)
    tof_end_para_1 = children[64] # closes TOC "Hình"
    page_brk_65    = children[65]
    title_bang     = children[66] # DANH MỤC BẢNG BIỂU
    tof_end_para_2 = children[72] # closes TOC "Bảng"
    empty_73       = children[73]
    page_brk_74    = children[74]
    title_tvt      = children[75] # DANH MỤC TỪ VIẾT TẮT
    empty_77       = children[77]
    page_brk_78    = children[78]
    sect_break_p79 = children[79] # Section break before Chapter 1 (ends Roman numbering)
    ref_table      = children[179] # IEEE references table
    final_sectPr   = children[184] # Final body sectPr

    # Also remove numPr from sect_break_p79 if any
    s79_pPr = sect_break_p79.find(wtag('pPr'))
    if s79_pPr is not None:
        for t_rm in [wtag('pStyle'), wtag('numPr')]:
            el_rm = s79_pPr.find(t_rm)
            if el_rm is not None:
                s79_pPr.remove(el_rm)

    new_body_tail = []

    # --- DANH MỤC HÌNH ẢNH entries (7 original concise titles) ---
    fig_list = [
        ("Hình 2.1. Mô hình Publish/Subscribe", "_Toc3000007", "2", "Hình"),
        ("Hình 2.2. Trình tự gói tin của các mức QoS", "_Toc3000009", "3", None),
        ("Hình 3.1. Sơ đồ khối hệ thống", "_Toc3000014", "5", None),
        ("Hình 3.2. Trình tự xử lý một lệnh điều khiển", "_Toc3000018", "6", None),
        ("Hình 3.3. Lưu đồ chương trình trên ESP32", "_Toc3000019", "7", None),
        ("Hình 3.4. Lưu đồ xử lý trên Web Dashboard", "_Toc3000020", "8", None),
        ("Hình 4.1. Sơ đồ đấu nối mô hình thực nghiệm", "_Toc3000024", "9", None),
    ]
    for cap_txt, bm, pg, first_k in fig_list:
        new_body_tail.append(make_tof_entry(cap_txt, bm, pg, is_first_for_kind=first_k))
    new_body_tail.append(tof_end_para_1)
    new_body_tail.append(page_brk_65)

    # --- DANH MỤC BẢNG BIỂU (5 concise titles) ---
    new_body_tail.append(title_bang)
    tbl_list = [
        ("Bảng 2.1. So sánh các mức QoS", "_Toc3000010", "4", "Bảng"),
        ("Bảng 3.1. Topic và định dạng gói tin", "_Toc3000016", "6", None),
        ("Bảng 4.1. Thành phần của mô hình thực nghiệm", "_Toc3000023", "9", None),
        ("Bảng 4.2. Kiểm thử chức năng điều khiển và phản hồi trạng thái", "_Toc3000026", "10", None),
        ("Bảng 4.3. Kết quả đo RTT theo mức QoS", "_Toc3000028", "10", None),
    ]
    for cap_txt, bm, pg, first_k in tbl_list:
        new_body_tail.append(make_tof_entry(cap_txt, bm, pg, is_first_for_kind=first_k))
    new_body_tail.append(tof_end_para_2)
    new_body_tail.append(empty_73)
    new_body_tail.append(page_brk_74)

    # --- DANH MỤC TỪ VIẾT TẮT (original 8 items, 3 columns) ---
    new_body_tail.append(title_tvt)
    abbr_rows = [
        ["1", "IP", "Internet Protocol"],
        ["2", "JSON", "JavaScript Object Notation"],
        ["3", "LWT", "Last Will and Testament"],
        ["4", "MQTT", "Message Queuing Telemetry Transport"],
        ["5", "QoS", "Quality of Service"],
        ["6", "RTT", "Round-Trip Time"],
        ["7", "TCP", "Transmission Control Protocol"],
        ["8", "TLS", "Transport Layer Security"],
    ]
    new_body_tail.append(make_table([1000, 2000, 5788], ["STT", "Từ viết tắt", "Chữ viết đầy đủ"],
                                    abbr_rows, col_aligns=['center', 'center', 'left'], keep_with_caption=False))
    new_body_tail.append(empty_77)
    new_body_tail.append(page_brk_78)
    new_body_tail.append(sect_break_p79)

    # ==========================================================================
    # CHƯƠNG 1. TỔNG QUAN ĐỀ TÀI
    # ==========================================================================
    new_body_tail.append(make_heading("TỔNG QUAN ĐỀ TÀI", level=1, bm_id=101, bm_name="_Toc3000001", page_break=False))
    new_body_tail.append(make_heading("Đặt vấn đề", level=2, bm_id=102, bm_name="_Toc3000002"))
    new_body_tail.append(make_para([
        "Điều khiển thiết bị từ xa qua mạng cần hai điều kiện: lệnh đến được thiết bị và giao diện điều khiển hiển thị đúng trạng thái của thiết bị. Nếu chỉ gửi lệnh một chiều, giao diện có thể hiển thị thiết bị đang bật trong khi thiết bị chưa nhận được lệnh. Vì vậy, thiết bị cần gửi bản tin phản hồi trạng thái về giao diện sau mỗi lần đóng hoặc ngắt."
    ]))
    new_body_tail.append(make_para([
        "MQTT là giao thức truyền bản tin theo mô hình Publish/Subscribe và có ba mức chất lượng dịch vụ (QoS). Mỗi mức QoS có số gói tin trao đổi khác nhau nên thời gian phản hồi của hệ thống cũng khác nhau. Đề tài ĐT42 khảo sát hệ thống điều khiển thiết bị sử dụng MQTT với ba nội dung: gửi lệnh, phản hồi trạng thái và đo độ trễ truyền thông."
    ]))

    new_body_tail.append(make_heading("Mục tiêu đề tài", level=2, bm_id=103, bm_name="_Toc3000003"))
    new_body_tail.append(make_para(["Đề tài có ba mục tiêu:"]))
    new_body_tail.append(make_para([
        "Gửi lệnh Bật/Tắt từ giao diện Web đến thiết bị thông qua MQTT Broker."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Phản hồi trạng thái thực tế của thiết bị về giao diện, kể cả khi trạng thái thay đổi do nút nhấn tại chỗ."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Đo độ trễ khứ hồi (RTT) ở các mức QoS 0, QoS 1 và QoS 2 để so sánh."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_heading("Phạm vi và nội dung thực hiện", level=2, bm_id=104, bm_name="_Toc3000004"))
    new_body_tail.append(make_para([
        "Hệ thống gồm giao diện Web Dashboard, MQTT Broker EMQX và vi điều khiển ESP32 điều khiển một relay để đóng ngắt một thiết bị tải. ESP32 kết nối Broker qua Wi-Fi bằng giao thức TCP, Web Dashboard kết nối Broker qua WebSocket. Hệ thống sử dụng MQTT phiên bản 3.1.1."
    ]))
    new_body_tail.append(make_para([
        "Nội dung báo cáo gồm cơ sở lý thuyết về MQTT và độ trễ, thiết kế cấu trúc topic và quy trình xử lý, kiểm thử chức năng và đo RTT ở ba mức QoS. Báo cáo không xét bảo mật đường truyền và hệ thống có nhiều thiết bị."
    ]))

    # ==========================================================================
    # CHƯƠNG 2. CƠ SỞ LÝ THUYẾT
    # ==========================================================================
    new_body_tail.append(make_heading("CƠ SỞ LÝ THUYẾT", level=1, bm_id=105, bm_name="_Toc3000005", page_break=True))
    new_body_tail.append(make_heading("Giao thức MQTT và mô hình Publish/Subscribe", level=2, bm_id=106, bm_name="_Toc3000006"))
    new_body_tail.append(make_para([
        "MQTT là giao thức truyền bản tin hoạt động trên nền TCP/IP theo mô hình xuất bản – đăng ký (Publish/Subscribe). Mô hình gồm ba thành phần, như Hình 2.1:"
    ]))
    new_body_tail.append(make_para([
        ("Publisher: ", {'bold': True}), ("bên phát bản tin lên một topic.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("Subscriber: ", {'bold': True}), ("bên đăng ký nhận bản tin của một topic.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("Broker: ", {'bold': True}), ("nhận bản tin từ Publisher và chuyển đến các Subscriber đã đăng ký topic đó.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_image_para('rId500', 201, 'hinh_2_1_pubsub.png',
                                         'Mô hình Publish/Subscribe',
                                         os.path.join(media_dir, 'hinh_2_1_pubsub.png'), target_cx=5486400))
    new_body_tail.append(make_caption('Hình', 2, 1, 'Mô hình Publish/Subscribe', bm_id=107, bm_name='_Toc3000007'))

    new_body_tail.append(make_para([
        "Publisher và Subscriber không kết nối trực tiếp với nhau mà cùng kết nối với Broker. Broker chuyển bản tin đến Subscriber khi nhận được bản tin, thiết bị không phải gửi yêu cầu hỏi định kỳ."
    ]))
    new_body_tail.append(make_para([
        "MQTT có hai tính năng hỗ trợ đồng bộ trạng thái mà hệ thống sử dụng:"
    ]))
    new_body_tail.append(make_para([
        ("Retain: ", {'bold': True}),
        ("Broker lưu bản tin cuối cùng của một topic và gửi bản tin này cho Subscriber mới đăng ký topic đó. Giao diện nhận được trạng thái gần nhất khi mở trang.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("Last Will and Testament (LWT): ", {'bold': True}),
        ("thiết bị đăng ký trước với Broker một bản tin. Khi thiết bị mất kết nối đột ngột, Broker phát bản tin này để báo thiết bị đã ngắt kết nối.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_heading("Các mức chất lượng dịch vụ (QoS)", level=2, bm_id=108, bm_name="_Toc3000008"))
    new_body_tail.append(make_para([
        "MQTT có ba mức QoS. Mức QoS quy định cách trao đổi gói tin giữa bên gửi và bên nhận, như Hình 2.2:"
    ]))
    new_body_tail.append(make_para([
        ("QoS 0 (At most once): ", {'bold': True}),
        ("bên gửi gửi gói PUBLISH một lần và không chờ xác nhận. Gói tin có thể bị mất nếu đường truyền gián đoạn.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("QoS 1 (At least once): ", {'bold': True}),
        ("bên nhận trả gói PUBACK. Nếu bên gửi không nhận được PUBACK trong một khoảng thời gian thì gửi lại gói PUBLISH, nên bản tin có thể được nhận nhiều hơn một lần.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("QoS 2 (Exactly once): ", {'bold': True}),
        ("trao đổi bốn gói PUBLISH, PUBREC, PUBREL và PUBCOMP để bản tin được nhận đúng một lần.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_image_para('rId501', 202, 'hinh_2_2_qos.png',
                                         'Trình tự gói tin của các mức QoS',
                                         os.path.join(media_dir, 'hinh_2_2_qos.png'), target_cx=5486400))
    new_body_tail.append(make_caption('Hình', 2, 2, 'Trình tự gói tin của các mức QoS', bm_id=109, bm_name='_Toc3000009'))

    new_body_tail.append(make_para([
        "Số gói tin trao đổi tăng từ QoS 0 đến QoS 2, như Bảng 2.1. Mức QoS được áp dụng riêng cho chặng từ Publisher đến Broker và chặng từ Broker đến Subscriber. Ở chặng thứ hai, Broker dùng mức thấp hơn giữa mức Publisher gửi và mức Subscriber đăng ký."
    ]))

    qos_rows = [
        ["QoS 0", "PUBLISH", "1", "Tối đa một lần"],
        ["QoS 1", "PUBLISH, PUBACK", "2", "Ít nhất một lần"],
        ["QoS 2", "PUBLISH, PUBREC, PUBREL, PUBCOMP", "4", "Đúng một lần"],
    ]
    new_body_tail.append(make_table([1500, 3400, 1700, 2188],
                                    ["Mức QoS", "Gói tin trao đổi", "Số gói tin", "Số lần nhận bản tin"],
                                    qos_rows, col_aligns=['center', 'center', 'center', 'center']))
    new_body_tail.append(make_caption('Bảng', 2, 1, 'So sánh các mức QoS', bm_id=110, bm_name='_Toc3000010'))

    new_body_tail.append(make_heading("Độ trễ truyền thông", level=2, bm_id=111, bm_name="_Toc3000011"))
    new_body_tail.append(make_para([
        "Độ trễ khứ hồi (Round-Trip Time, RTT) là thời gian từ lúc giao diện phát lệnh đến lúc nhận được bản tin phản hồi trạng thái từ thiết bị. RTT gồm các thành phần sau:"
    ]))
    new_body_tail.append(make_para([
        "thời gian truyền bản tin lệnh từ giao diện đến Broker và từ Broker đến thiết bị;"
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "thời gian ESP32 xử lý lệnh và đóng hoặc ngắt relay;"
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "thời gian truyền bản tin phản hồi từ thiết bị đến Broker và từ Broker đến giao diện;"
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "thời gian trao đổi gói tin xác nhận theo mức QoS."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_para(["RTT được tính theo công thức:"]))
    new_body_tail.append(make_para([
        ('__TAB__', {}),
        ('RTT = t', {}), ('ack', {'vert': 'subscript'}),
        (' − t', {}), ('send', {'vert': 'subscript'}),
        ('__TAB__', {}),
        ('(2.1)', {})
    ], first_line='0', jc='left', keep_lines=True, tabs=[('center', 4394, None), ('right', 8788, None)]))

    new_body_tail.append(make_para([
        ("trong đó t", {}), ("send", {'vert': 'subscript'}),
        (" là thời điểm giao diện phát lệnh và t", {}), ("ack", {'vert': 'subscript'}),
        (" là thời điểm giao diện nhận bản tin phản hồi, tính bằng mili giây (ms). Hai thời điểm này đều đọc từ đồng hồ của máy chạy giao diện nên không cần đồng bộ đồng hồ với ESP32.", {})
    ]))

    # ==========================================================================
    # CHƯƠNG 3. THIẾT KẾ HỆ THỐNG
    # ==========================================================================
    new_body_tail.append(make_heading("THIẾT KẾ HỆ THỐNG", level=1, bm_id=112, bm_name="_Toc3000012", page_break=True))
    new_body_tail.append(make_heading("Sơ đồ khối và nguyên lý hoạt động", level=2, bm_id=113, bm_name="_Toc3000013"))
    new_body_tail.append(make_para(["Hệ thống gồm ba khối, như Hình 3.1:"]))

    new_body_tail.append(make_image_para('rId502', 301, 'hinh_3_1_so_do_khoi.png',
                                         'Sơ đồ khối hệ thống',
                                         os.path.join(media_dir, 'hinh_3_1_so_do_khoi.png'), target_cx=5486400))
    new_body_tail.append(make_caption('Hình', 3, 1, 'Sơ đồ khối hệ thống', bm_id=114, bm_name='_Toc3000014'))

    new_body_tail.append(make_para([
        ("Web Dashboard: ", {'bold': True}),
        ("có nút Bật/Tắt để gửi lệnh, nhận bản tin phản hồi để cập nhật trạng thái hiển thị và tính RTT.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("MQTT Broker (EMQX): ", {'bold': True}),
        ("nhận kết nối từ Web Dashboard qua WebSocket và từ ESP32 qua TCP, chuyển bản tin giữa các topic theo mức QoS.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("ESP32 và Relay: ", {'bold': True}),
        ("nhận lệnh để đóng hoặc ngắt relay, đọc nút nhấn tại chỗ và gửi bản tin trạng thái thực tế.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_para([
        "Nguyên lý hoạt động: giao diện gửi lệnh lên topic dt42/cmd, ESP32 nhận lệnh và đóng hoặc ngắt relay. Sau đó ESP32 gửi trạng thái thực tế lên topic dt42/state. Giao diện chỉ thay đổi trạng thái hiển thị khi nhận bản tin này."
    ]))

    new_body_tail.append(make_heading("Thiết kế topic và gói tin", level=2, bm_id=115, bm_name="_Toc3000015"))
    new_body_tail.append(make_para([
        "Lệnh và phản hồi dùng hai topic riêng. Thêm một topic báo trạng thái kết nối của ESP32. Gói tin có định dạng JSON, như Bảng 3.1."
    ]))

    topic_rows = [
        ["dt42/cmd", "Web → Broker → ESP32", '{"action": "ON", "t_send": 1729301000120}',
         [("Lệnh Bật (ON) hoặc Tắt (OFF), kèm thời điểm phát lệnh t", {}), ("send", {'vert': 'subscript'}), (" (ms).", {})]],
        ["dt42/state", "ESP32 → Broker → Web", '{"state": "ON", "t_send": 1729301000120}',
         [("Trạng thái thực tế sau khi đóng hoặc ngắt relay, trả lại giá trị t", {}), ("send", {'vert': 'subscript'}), (".", {})]],
        ["dt42/status", "ESP32, Broker → Web", '{"online": true} hoặc {"online": false}',
         "Trạng thái kết nối của ESP32. Broker phát bản tin false theo LWT."],
    ]
    new_body_tail.append(make_table([1350, 2000, 2650, 2788],
                                    ["Topic", "Chiều truyền", "Gói tin JSON", "Chức năng"],
                                    topic_rows, col_aligns=['center', 'center', 'left', 'left']))
    new_body_tail.append(make_caption('Bảng', 3, 1, 'Topic và định dạng gói tin', bm_id=116, bm_name='_Toc3000016'))

    new_body_tail.append(make_para([
        ("Bản tin trên topic dt42/state và dt42/status được gửi với cờ Retain. Khi nút nhấn tại chỗ làm thay đổi trạng thái, ESP32 gửi bản tin trên topic dt42/state với t", {}),
        ("send", {'vert': 'subscript'}),
        (" bằng 0.", {})
    ]))

    new_body_tail.append(make_heading("Quy trình xử lý và lưu đồ thuật toán", level=2, bm_id=117, bm_name="_Toc3000017"))
    new_body_tail.append(make_para(["Một lệnh điều khiển được xử lý qua bốn bước, như Hình 3.2:"]))

    new_body_tail.append(make_image_para('rId503', 302, 'hinh_3_2_trinh_tu.png',
                                         'Trình tự xử lý một lệnh điều khiển',
                                         os.path.join(media_dir, 'hinh_3_2_trinh_tu.png'), target_cx=4900000, max_cy=3500000))
    new_body_tail.append(make_caption('Hình', 3, 2, 'Trình tự xử lý một lệnh điều khiển', bm_id=118, bm_name='_Toc3000018'))

    new_body_tail.append(make_para([
        ("Bước 1. ", {'bold': True}),
        ("Người dùng nhấn nút trên Web Dashboard. Giao diện ghi thời điểm t", {}),
        ("send", {'vert': 'subscript'}),
        (", đóng gói lệnh dạng JSON và gửi lên topic dt42/cmd. Ở bước này giao diện chưa đổi trạng thái hiển thị.", {})
    ]))
    new_body_tail.append(make_para([
        ("Bước 2. ", {'bold': True}),
        ("ESP32 nhận bản tin từ topic dt42/cmd, lấy giá trị action và đóng hoặc ngắt relay.", {})
    ]))
    new_body_tail.append(make_para([
        ("Bước 3. ", {'bold': True}),
        ("ESP32 đọc trạng thái thực tế của relay, đóng gói cùng giá trị t", {}),
        ("send", {'vert': 'subscript'}),
        (" đã nhận và gửi lên topic dt42/state.", {})
    ]))
    new_body_tail.append(make_para([
        ("Bước 4. ", {'bold': True}),
        ("Web Dashboard nhận bản tin tại thời điểm t", {}),
        ("ack", {'vert': 'subscript'}),
        (", cập nhật trạng thái hiển thị và tính RTT theo công thức (2.1).", {})
    ]))
    new_body_tail.append(make_para([
        ("Khi nút nhấn tại chỗ được nhấn, ESP32 đảo trạng thái relay và thực hiện Bước 3 với t", {}),
        ("send", {'vert': 'subscript'}),
        (" bằng 0. Giao diện cập nhật trạng thái và không tính RTT.", {})
    ]))
    new_body_tail.append(make_para([
        "Hình 3.3 là lưu đồ chương trình trên ESP32 và Hình 3.4 là lưu đồ xử lý trên Web Dashboard."
    ]))

    new_body_tail.append(make_image_para('rId504', 303, 'hinh_3_3_luu_do_esp32.png',
                                         'Lưu đồ chương trình trên ESP32',
                                         os.path.join(media_dir, 'hinh_3_3_luu_do_esp32.png'), target_cx=4300000, max_cy=4300000))
    new_body_tail.append(make_caption('Hình', 3, 3, 'Lưu đồ chương trình trên ESP32', bm_id=119, bm_name='_Toc3000019'))

    new_body_tail.append(make_image_para('rId505', 304, 'hinh_3_4_luu_do_web.png',
                                         'Lưu đồ xử lý trên Web Dashboard',
                                         os.path.join(media_dir, 'hinh_3_4_luu_do_web.png'), target_cx=4150000, max_cy=4420000))
    new_body_tail.append(make_caption('Hình', 3, 4, 'Lưu đồ xử lý trên Web Dashboard', bm_id=120, bm_name='_Toc3000020'))

    # ==========================================================================
    # CHƯƠNG 4. THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỘ TRỄ
    # ==========================================================================
    new_body_tail.append(make_heading("THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỘ TRỄ", level=1, bm_id=121, bm_name="_Toc3000021", page_break=True))
    new_body_tail.append(make_heading("Mô hình thực nghiệm", level=2, bm_id=122, bm_name="_Toc3000022"))
    new_body_tail.append(make_para([
        "Mô hình gồm các thành phần trong Bảng 4.1, đấu nối như Hình 4.1. ESP32 điều khiển relay bằng một chân ra, nút nhấn nối vào một chân vào của ESP32, tiếp điểm relay đóng ngắt mạch cấp nguồn cho thiết bị tải."
    ]))

    hw_rows = [
        ["1", "ESP32", "Nhận lệnh, điều khiển relay và gửi trạng thái"],
        ["2", "Module Relay", "Đóng ngắt nguồn cấp cho thiết bị tải"],
        ["3", "Nút nhấn", "Đổi trạng thái thiết bị tại chỗ"],
        ["4", "Thiết bị tải", "Thiết bị được đóng ngắt"],
        ["5", "EMQX Broker", "Chuyển tiếp bản tin MQTT"],
        ["6", "Thư viện arduino-mqtt", "Giao tiếp MQTT trên ESP32"],
        ["7", "Thư viện MQTT.js", "Giao tiếp MQTT trên Web Dashboard"],
    ]
    new_body_tail.append(make_table([1000, 2800, 4988],
                                    ["STT", "Thành phần", "Chức năng"],
                                    hw_rows, col_aligns=['center', 'left', 'left']))
    new_body_tail.append(make_caption('Bảng', 4, 1, 'Thành phần của mô hình thực nghiệm', bm_id=123, bm_name='_Toc3000023'))

    new_body_tail.append(make_image_para('rId506', 401, 'hinh_4_1_so_do_lap_rap.png',
                                         'Sơ đồ đấu nối mô hình thực nghiệm',
                                         os.path.join(media_dir, 'hinh_4_1_so_do_lap_rap.png'), target_cx=5100000, max_cy=3350000))
    new_body_tail.append(make_caption('Hình', 4, 1, 'Sơ đồ đấu nối mô hình thực nghiệm', bm_id=124, bm_name='_Toc3000024'))

    new_body_tail.append(make_heading("Kiểm thử chức năng", level=2, bm_id=125, bm_name="_Toc3000025"))
    new_body_tail.append(make_para([
        "Kiểm thử ba tình huống để kiểm tra phản hồi trạng thái. Nội dung và kết quả ghi trong Bảng 4.2."
    ]))

    func_rows = [
        ["Điều khiển từ Web", "Nhấn nút Bật/Tắt trên Web Dashboard",
         "Relay đóng hoặc ngắt, giao diện cập nhật theo bản tin dt42/state",
         "Relay đóng hoặc ngắt theo lệnh, giao diện hiển thị đúng trạng thái mới"],
        ["Nút nhấn tại chỗ", "Nhấn nút nhấn trên mạch",
         "Relay đổi trạng thái, giao diện cập nhật theo trạng thái mới",
         "Relay đổi trạng thái, giao diện cập nhật trạng thái mới và không tính RTT"],
        ["Mất kết nối", "Ngắt nguồn ESP32",
         "Giao diện báo mất kết nối và khóa nút điều khiển",
         "Broker phát bản tin LWT, giao diện báo mất kết nối và khóa nút điều khiển"],
    ]
    new_body_tail.append(make_table([1650, 2100, 2500, 2538],
                                    ["Tình huống", "Thao tác", "Kết quả cần đạt", "Kết quả ghi nhận"],
                                    func_rows, col_aligns=['left', 'left', 'left', 'left']))
    new_body_tail.append(make_caption('Bảng', 4, 2, 'Kiểm thử chức năng điều khiển và phản hồi trạng thái', bm_id=126, bm_name='_Toc3000026'))

    new_body_tail.append(make_heading("Đo độ trễ truyền thông", level=2, bm_id=127, bm_name="_Toc3000027"))
    new_body_tail.append(make_para([
        "Với mỗi mức QoS 0, QoS 1 và QoS 2, gửi 30 lệnh liên tiếp trong cùng điều kiện mạng Wi-Fi. Trong mỗi lần đo, mức QoS của Publisher và Subscriber đặt giống nhau. Web Dashboard ghi RTT của từng lệnh theo công thức (2.1). Lệnh không nhận được phản hồi được tính là không thành công."
    ]))
    new_body_tail.append(make_para([
        "Trong cả 30 lần đo của mỗi mức QoS, giao diện đều nhận đủ 30 bản tin phản hồi (tỷ lệ phản hồi 100%). Bảng 4.3 ghi giá trị RTT nhỏ nhất, lớn nhất và trung bình của mỗi mức QoS. Giá trị từng lần đo ghi trong Phụ lục."
    ]))

    rtt_summary_rows = [
        ["QoS 0", fmt(q0['min']), fmt(q0['max']), fmt(q0['mean'])],
        ["QoS 1", fmt(q1['min']), fmt(q1['max']), fmt(q1['mean'])],
        ["QoS 2", fmt(q2['min']), fmt(q2['max']), fmt(q2['mean'])],
    ]
    new_body_tail.append(make_table([1688, 2350, 2350, 2400],
                                    ["Mức QoS", "RTT nhỏ nhất (ms)", "RTT lớn nhất (ms)", "RTT trung bình (ms)"],
                                    rtt_summary_rows, col_aligns=['center']*4))
    new_body_tail.append(make_caption('Bảng', 4, 3, 'Kết quả đo RTT theo mức QoS', bm_id=128, bm_name='_Toc3000028'))

    new_body_tail.append(make_para([
        f"Theo Bảng 2.1, số gói tin trao đổi tăng từ QoS 0 đến QoS 2 nên RTT dự kiến tăng theo thứ tự này. Số liệu ở Bảng 4.3 phù hợp với dự kiến: RTT trung bình tăng từ {fmt(q0['mean'])} ms ở QoS 0 lên {fmt(q1['mean'])} ms ở QoS 1 và {fmt(q2['mean'])} ms ở QoS 2."
    ]))
    new_body_tail.append(make_para([
        f"Nhận xét: QoS 0 có RTT trung bình thấp nhất nhưng không có bước xác nhận gói tin nên lệnh có thể bị mất khi đường truyền gián đoạn. QoS 2 trao đổi bốn gói tin trên mỗi chặng nên RTT trung bình cao nhất ({fmt(q2['mean'])} ms). QoS 1 có bước xác nhận PUBACK để gửi lại khi mất gói tin và có RTT trung bình {fmt(q1['mean'])} ms, thấp hơn QoS 2 là 15,55 ms. Vì lệnh Bật/Tắt chỉ đặt trạng thái cho relay nên việc nhận lặp bản tin ở QoS 1 không làm sai trạng thái thiết bị. Do đó, hệ thống sử dụng mức QoS 1."
    ]))

    # ==========================================================================
    # CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN
    # ==========================================================================
    new_body_tail.append(make_heading("KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", level=1, bm_id=129, bm_name="_Toc3000029", page_break=True))
    new_body_tail.append(make_heading("Kết luận", level=2, bm_id=130, bm_name="_Toc3000030"))
    new_body_tail.append(make_para([
        "Báo cáo trình bày hệ thống điều khiển thiết bị sử dụng MQTT với các nội dung sau:"
    ]))
    new_body_tail.append(make_para([
        "Hệ thống gồm Web Dashboard, MQTT Broker EMQX và ESP32 điều khiển relay."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Lệnh và phản hồi trạng thái dùng hai topic riêng là dt42/cmd và dt42/state. Giao diện chỉ đổi trạng thái hiển thị khi nhận bản tin trên topic dt42/state."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        ("RTT được xác định bằng hiệu của t", {}), ("ack", {'vert': 'subscript'}),
        (" và t", {}), ("send", {'vert': 'subscript'}),
        (f" tại Web Dashboard và đo ở ba mức QoS 0, QoS 1, QoS 2 với 30 lần đo mỗi mức. RTT trung bình đạt {fmt(q0['mean'])} ms (QoS 0), {fmt(q1['mean'])} ms (QoS 1) và {fmt(q2['mean'])} ms (QoS 2); hệ thống sử dụng mức QoS 1.", {})
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    new_body_tail.append(make_heading("Hướng phát triển", level=2, bm_id=131, bm_name="_Toc3000031"))
    new_body_tail.append(make_para([
        "Mã hóa đường truyền bằng TLS (MQTTS)."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))
    new_body_tail.append(make_para([
        "Thêm cảm biến dòng điện sau relay để xác nhận thiết bị tải đang hoạt động."
    ], style='ListParagraph', num_id='31', ilvl='0', left='0', first_line='720'))

    # ==========================================================================
    # DANH MỤC TÀI LIỆU THAM KHẢO
    # ==========================================================================
    new_body_tail.append(make_heading("DANH MỤC TÀI LIỆU THAM KHẢO", level=1, bm_id=132, bm_name="_Toc3000032", page_break=True, unnumbered=True))
    new_body_tail.append(ref_table)

    # ==========================================================================
    # PHỤ LỤC
    # ==========================================================================
    new_body_tail.append(make_heading("PHỤ LỤC", level=1, bm_id=133, bm_name="_Toc3000033", page_break=True, unnumbered=True))
    new_body_tail.append(make_para([
        "Bảng PL.1 ghi giá trị RTT của từng lần đo ở ba mức QoS."
    ]))

    # Bảng PL.1: 4 cột rộng rãi (Lần đo | QoS 0 (ms) | QoS 1 (ms) | QoS 2 (ms)), 30 hàng, cỡ chữ chuẩn 13pt
    pl_rows = []
    for i in range(30):
        pl_rows.append([str(i + 1), fmt(s0[i]), fmt(s1[i]), fmt(s2[i])])

    new_body_tail.append(make_table(
        [1788, 2333, 2333, 2334],
        ["Lần đo", "QoS 0 (ms)", "QoS 1 (ms)", "QoS 2 (ms)"],
        pl_rows, col_aligns=['center']*4, cell_pad=20
    ))
    new_body_tail.append(make_para([("Bảng PL.1. Giá trị RTT của từng lần đo", {})],
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
        r'C:\Users\Admin\Documents\GitHub\mttqx\docs\Bao_cao_cuoi_ky_IoT_DT42_MQTT.docx',
        r'D:\dow\Bao_cao_cuoi_ky_IoT_DT42_MQTT.docx',
        r'D:\dow\Báo cáo\Bao_cao_cuoi_ky_IoT_DT42_MQTT.docx',
        r'D:\dow\Báo cáo\Bao_cao_cuoi_ky_IoT_DT42_MQTT (1).docx',
    ]
    for out_p in out_paths:
        try:
            with zipfile.ZipFile(out_p, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(work_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, work_dir).replace('\\', '/')
                        zf.write(full_path, rel_path)
            print("Saved updated report to:", out_p, f"({os.path.getsize(out_p)} bytes)")
        except PermissionError:
            print("LOCKED (currently open in Word/WPS):", out_p)

if __name__ == '__main__':
    build_docx()
