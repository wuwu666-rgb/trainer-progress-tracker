import unittest, tempfile
from pathlib import Path
import app as m

class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent, ignore_cleanup_errors=True); self.old=m.ROOT; m.ROOT=Path(self.tmp.name)
        with m.db() as c:
            c.executescript('CREATE TABLE users(id TEXT PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT); CREATE TABLE records(id TEXT PRIMARY KEY,kind TEXT,owner TEXT,profile TEXT,data TEXT); CREATE TABLE receipts(id TEXT PRIMARY KEY,user TEXT,payload TEXT,response TEXT);')
        self.a=m.app.test_client(); self.b=m.app.test_client()
    def tearDown(self): m.ROOT=self.old; self.tmp.cleanup()
    def call(self,c,path,d=None,method='POST'):
        token=c.get('/api/context').json['data']['csrf_token']
        return c.open('/api/'+path,method=method,json=d,headers={'X-CSRF-Token':token})
    def test_flow_and_permissions(self):
        for c,email,role in [(self.a,'trainer@test.com','trainer'),(self.b,'client@test.com','client')]:
            self.assertEqual(self.call(c,'register',dict(name=role,email=email,password='password123',role=role)).status_code,200)
        p=self.call(self.a,'records/clients',{'name':'Alex','goals':'Strength'}).json['data']
        self.assertEqual(self.b.get('/api/records/clients').json['data'],[])
        inv=self.call(self.a,'records/invitations',dict(profile=p['id'],email='client@test.com')).json['data']
        self.assertEqual(self.call(self.b,'records/invitations/'+inv['id'],{'decision':'accept'},'PUT').status_code,200)
        self.assertEqual(len(self.b.get('/api/records/clients').json['data']),1)
        exercises=[dict(name='Squat',target_sets=3,target_reps=10)]
        plan=self.call(self.a,'records/plans',dict(profile=p['id'],name='Leg day',exercises=exercises)).json['data']
        s=self.call(self.b,'records/sessions',dict(profile=p['id'],plan_id=plan['id'],name='Leg day',device_id='test',status='in_progress',workout_date='2026-01-01')).json['data']
        body=s['data']|dict(base_version=1,operation_id='stable',status='completed')
        body['exercises'][0]['sets']=[dict(actual_reps=10,weight_lb='50')]
        for _ in range(2): self.assertEqual(self.call(self.b,'records/sessions/'+s['id'],body,'PUT').status_code,200)
        self.assertEqual(len(self.b.get('/api/records/sessions').json['data']),1)
        self.assertEqual(self.call(self.a,'records/sessions/'+s['id'],body|{'operation_id':'other'},'PUT').status_code,403)
        self.assertEqual(self.call(self.b,'records/sessions/'+s['id'],body|{'operation_id':'stale'},'PUT').status_code,409)
        self.assertEqual(self.a.post('/api/logout').status_code,400)
if __name__=='__main__': unittest.main()

