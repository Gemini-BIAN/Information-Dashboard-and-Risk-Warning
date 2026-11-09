import hashlib,json,subprocess
from datetime import timedelta
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect
from sqlalchemy import select
from scm.database.models import Event
from scm.database.session import session_factory
from scm.settings import ROOT,TIMEZONE,utcnow
from scm.ui.presentation import build_views,filter_views
out=ROOT/'docs/ui_uat'
result={'status':'RUNNING','scope':'fresh-process/fresh-browser readonly Live ordering check only','verified_at':utcnow().astimezone(TIMEZONE).isoformat(),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'checks':[]}
try:
 with session_factory()() as s:
  views=build_views(s,list(s.scalars(select(Event))),'live')
  today=utcnow().astimezone(TIMEZONE).date()
  selected=filter_views(views,period=(today-timedelta(days=30),today))[:8]
  expected=[v.title for v in selected]
  result['expected']=[{'id':v.event.id,'title':v.title,'tier':v.tier,'relevance':v.relevance_score} for v in selected]
  assert expected and 'PET Spunbond' in expected[0]
 with httpx.Client(trust_env=False,timeout=10) as c:
  r=c.get('http://127.0.0.1:8503/_stcore/health');assert r.status_code==200
 result['checks'].append('new local server health 200')
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  context=browser.new_context(viewport={'width':1366,'height':768},device_scale_factor=1)
  page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  page.route('**/*',lambda route:route.continue_() if route.request.url.startswith('http://127.0.0.1:8503/') else route.abort())
  page.set_default_timeout(15000);expect.set_options(timeout=15000)
  page.goto('http://127.0.0.1:8503',wait_until='networkidle',timeout=30000)
  expect(page.get_by_role('heading',name='供应链例外与风险指挥台',exact=True)).to_be_visible()
  expect(page.get_by_text('LIVE · 真实来源',exact=True)).to_be_visible()
  expect(page.locator('.scm-event-title')).to_have_count(len(expected))
  expect(page.locator('.scm-event-title').first).to_have_text(expected[0])
  actual=[x.strip() for x in page.locator('.scm-event-title').all_text_contents()]
  result['actual']=actual
  assert actual==expected,'Browser sequence differs from unchanged backend sequence'
  assert not errors
  expect(page.get_by_test_id('stException')).to_have_count(0)
  expect(page.get_by_test_id('stMetricValue')).to_have_count(4)
  expect(page.get_by_role('link',name='查看原始来源',exact=True)).to_have_count(len(expected))
  expect(page.get_by_role('button',name='导出筛选结果 CSV',exact=True)).to_be_visible()
  page.wait_for_load_state('networkidle',timeout=10000)
  screenshot=out/'after-live-fresh-1366.png';page.screenshot(path=str(screenshot))
  result['screenshot']={'path':str(screenshot.relative_to(ROOT)),'sha256':hashlib.sha256(screenshot.read_bytes()).hexdigest(),'viewport':{'width':1366,'height':768},'unaltered':True}
  result['browser']=browser.version;result['page_errors']=errors
  result['checks']+=['first card is original PET Spunbond trade article','all eight displayed positions exactly match existing backend sort','new browser context with no reused session/storage','no browser pageerror or Streamlit exception']
  context.close();browser.close()
 result['status']='PASS'
except Exception as exc:
 result['status']='FAIL';result['error']=type(exc).__name__+': '+str(exc)
 raise
finally:
 result['presentation_sha256']=hashlib.sha256((ROOT/'src/scm/ui/presentation.py').read_bytes()).hexdigest()
 (out/'sorting-fresh-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'status':result['status'],'checks':result['checks'],'error':result.get('error')},ensure_ascii=False))
