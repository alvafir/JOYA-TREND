from __future__ import annotations
from datetime import datetime
import hashlib,json
import pandas as pd
from engines.market_engine import analyze_all_markets
from repositories.data_lake import connect,initialize_data_lake,save_analysis
def create_job(title,fixtures,groups):
 initialize_data_lake(); ids=[int((f.get('fixture',{}) or {}).get('id')) for f in fixtures if (f.get('fixture',{}) or {}).get('id')]
 payload={'title':title,'fixtures':ids,'groups':sorted(groups)}; jid=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:18]; now=datetime.utcnow().isoformat(timespec='seconds')
 with connect() as c:
  c.execute("INSERT OR REPLACE INTO jobs(job_id,title,status,total,completed,failed,payload_json,updated_at) VALUES(?,?,'ready',?,0,0,?,?)",(jid,title,len(fixtures),json.dumps(payload,ensure_ascii=False),now)); c.execute("DELETE FROM job_items WHERE job_id=?",(jid,))
  for pos,f in enumerate(fixtures,1):
   fid=(f.get('fixture',{}) or {}).get('id')
   if fid: c.execute("INSERT INTO job_items(job_id,position,fixture_id,fixture_json,status,error,updated_at) VALUES(?,?,?,?,'pending',NULL,?)",(jid,pos,int(fid),json.dumps(f,ensure_ascii=False),now))
  c.commit()
 return jid
def refresh_job_status(jid):
 initialize_data_lake()
 with connect() as c:
  job=c.execute('SELECT * FROM jobs WHERE job_id=?',(jid,)).fetchone()
  if not job:return {}
  rows=c.execute('SELECT status,COUNT(*) count FROM job_items WHERE job_id=? GROUP BY status',(jid,)).fetchall(); d={r['status']:int(r['count']) for r in rows}; comp=d.get('completed',0); fail=d.get('failed',0); pend=d.get('pending',0); status='completed' if pend==0 else 'paused'; now=datetime.utcnow().isoformat(timespec='seconds')
  c.execute('UPDATE jobs SET status=?,completed=?,failed=?,updated_at=? WHERE job_id=?',(status,comp,fail,now,jid)); c.commit()
 return {'job_id':jid,'title':job['title'],'total':int(job['total']),'completed':comp,'failed':fail,'pending':pend,'status':status}
def run_job_batch(jid,groups,batch_size=10,progress_callback=None):
 initialize_data_lake()
 with connect() as c: rows=c.execute("SELECT * FROM job_items WHERE job_id=? AND status='pending' ORDER BY position LIMIT ?",(jid,int(batch_size))).fetchall()
 for i,r in enumerate(rows,1):
  try:
   fixture=json.loads(r['fixture_json']); summary,table=analyze_all_markets(fixture,groups)
   if summary: save_analysis(summary,table)
   st='completed'; err=None
  except Exception as e: st='failed'; err=str(e)[:500]
  now=datetime.utcnow().isoformat(timespec='seconds')
  with connect() as c: c.execute('UPDATE job_items SET status=?,error=?,updated_at=? WHERE job_id=? AND fixture_id=?',(st,err,now,jid,int(r['fixture_id']))); c.commit()
  if progress_callback: progress_callback(i,len(rows))
 return refresh_job_status(jid)
def list_jobs():
 initialize_data_lake()
 with connect() as c: rows=c.execute('SELECT job_id,title,status,total,completed,failed,updated_at FROM jobs ORDER BY updated_at DESC').fetchall()
 return pd.DataFrame([dict(r) for r in rows])
