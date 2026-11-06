"""Original UI styling. Does not hide/modify browser, enterprise or external overlays."""

CSS = """<style>
[data-testid="stMain"] .block-container {max-width:1400px;padding:1.1rem 1.8rem 3rem;}
[data-testid="stAppViewContainer"] {background:#f4f7fa;}
[data-testid="stAppViewContainer"] h1 {font-size:1.5rem;line-height:1.35;color:#102d44;letter-spacing:-.02em;}
[data-testid="stAppViewContainer"] h2 {font-size:1.12rem;color:#16384d;}
[data-testid="stAppViewContainer"] h3 {font-size:1rem;color:#16384d;}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid #dbe4ec;}
@media(min-width:900px){[data-testid="stSidebar"]{width:240px!important;min-width:240px!important;max-width:240px!important;}}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top:1.2rem;}
[data-testid="stMetric"] {background:#fff;border:1px solid #dbe4ec;border-radius:10px;padding:.8rem 1rem;}
[data-testid="stMetricLabel"] {color:#405a6c;}
[data-testid="stMetricValue"] {color:#102d44;font-size:1.7rem;}
[class*="st-key-scm_event_"] {background:#fff;border-radius:10px;}
[data-testid="stAlert"] {padding:.55rem .8rem;}
.scm-brand {display:flex;align-items:center;gap:10px;margin:0 0 24px;color:#143347;}
.scm-mark {background:#123b50;color:white;font-weight:750;font-size:19px;border-radius:8px;padding:6px 10px;}
.scm-brand strong {font-size:19px;letter-spacing:.05em;}
.scm-brand small {display:block;color:#5b7080;font-size:11px;}
.scm-context {background:#e9f1f6;border:1px solid #cfdee7;border-radius:8px;padding:8px 12px;color:#294b60;font-size:12px;line-height:1.65;margin:0 0 12px;}
.scm-context .scm-mode {color:#07594d;font-weight:750;margin-right:12px;}
.scm-context.demo .scm-mode {color:#86580c;}
.scm-card-head {display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px;}
.scm-pill {display:inline-block;border:1px solid #d5e0e8;border-radius:5px;padding:2px 7px;font-size:11px;font-weight:650;background:#f2f6f9;color:#355369;line-height:1.5;}
.scm-pill.teal {background:#e7f5f0;color:#07594d;border-color:#a3d4c6;}
.scm-pill.amber {background:#fff5df;color:#7c4e00;border-color:#ead098;}
.scm-pill.red {background:#fff0f0;color:#9c2626;border-color:#efc3c3;}
.scm-event-title {font-size:15px;font-weight:700;line-height:1.6;color:#16384d;overflow-wrap:anywhere;margin:0 0 6px;}
.scm-summary {font-size:12px;line-height:1.65;color:#435e70;margin:0 0 7px;}
.scm-meta {font-size:11px;line-height:1.7;color:#546b7b;overflow-wrap:anywhere;margin:2px 0;}
.scm-empty {text-align:center;padding:34px 20px;border:1px dashed #b8cbd8;background:#fff;border-radius:10px;color:#496174;}
.scm-empty strong {display:block;color:#14384f;font-size:17px;margin-bottom:8px;}
@media(max-width:800px){[data-testid="stMain"] .block-container {padding:1rem .8rem 2rem;}.scm-context{font-size:11px;}}
</style>"""
