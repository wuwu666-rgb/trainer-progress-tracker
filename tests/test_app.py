import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app, uid, today

class TrackerTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app({'TESTING':True,'DATABASE':str(Path(self.tmp.name)/'test.db')})
        self.trainer=self.app.test_client();self.client=self.app.test_client();self.other=self.app.test_client()
        self.u=self.register(self.trainer,'trainer','trainer@test.com')
        self.c=self.register(self.client,'client','client@test.com')
        self.register(self.other,'trainer','other@test.com')
        self.profile=self.send(self.trainer,'/clients',{'name':'Alex','goals':'Strength'}).json['data']
        i=self.send(self.trainer,'/invitations',{'profile_id':self.profile['id'],'client_email':'client@test.com'}).json['data']
        self.send(self.client,'/invitations/'+i['id']+'/respond',{'decision':'accept'})
        self.exercise={'id':uid(),'name':'Squat','target_sets':3,'target_reps':10}
    def tearDown(self):self.tmp.cleanup()
    def send(self,browser,path,payload,method='POST'):
        csrf=browser.get('/api/context').json['data']['csrf_token']
        return browser.open('/api'+path,method=method,json=payload,headers={'X-CSRFToken':csrf})
    def register(self,b,role,email):return self.send(b,'/register',{'name':role,'email':email,'password':'testpass123','role':role}).json['data']
    def planned(self):
        t=self.send(self.trainer,'/templates',{'name':'Plan','exercises':[self.exercise]}).json['data']
        p=self.send(self.trainer,'/plans',{'profile_id':self.profile['id'],'source_template_id':t['id'],'name':'Plan','exercises':t['exercises']}).json['data']
        return t,p
    def prepared(self):
        t,p=self.planned()
        payload={'operation_id':uid(),'device_id':'device1','profile_id':self.profile['id'],'plan_id':p['id'],'name':'Plan'}
        return self.send(self.client,'/sessions/prepare',payload).json['data']
    def upload(self,s):return {'operation_id':uid(),'device_id':'device1','base_version':s['version'],'name':s['name'],'workout_date':today(),'status':'completed','exercises':[dict(self.exercise,sets=[{'actual_reps':10,'weight_lb':'25.5'}])]}
    def test_csrf_required(self):
        self.assertEqual(self.trainer.post('/api/clients',json={'name':'bad'}).status_code,400)
    def test_role_and_private_access(self):
        self.assertEqual(self.send(self.client,'/clients',{'name':'bad'}).status_code,403)
        self.assertEqual(self.other.get('/api/clients/'+self.profile['id']+'/history').status_code,403)
        self.assertEqual(self.other.get('/api/clients').json['data'],[])
    def test_template_snapshot_independent(self):
        t,p=self.planned()
        self.send(self.trainer,'/templates/'+t['id'],{'name':'Changed','exercises':[dict(self.exercise,name='New exercise')]},'PUT')
        self.assertEqual(self.client.get('/api/plans').json['data'][0]['exercises'][0]['name'],'Squat')
    def test_sync_idempotency_and_conflict(self):
        s=self.prepared();x=self.upload(s)
        first=self.send(self.client,'/sessions/'+s['id'],x,'PUT');self.assertEqual(first.status_code,200)
        replay=self.send(self.client,'/sessions/'+s['id'],x,'PUT');self.assertEqual(first.json,replay.json)
        self.assertEqual(len(self.client.get('/api/clients/'+self.profile['id']+'/history').json['data']),1)
        x['name']='Different'
        self.assertEqual(self.send(self.client,'/sessions/'+s['id'],x,'PUT').status_code,409)
        x['operation_id']=uid()
        self.assertEqual(self.send(self.client,'/sessions/'+s['id'],x,'PUT').status_code,409)
    def test_recorder_device_and_owner(self):
        s=self.prepared();x=self.upload(s)
        self.assertEqual(self.send(self.trainer,'/sessions/'+s['id'],x,'PUT').status_code,403)
        x['device_id']='device2'
        self.assertEqual(self.send(self.client,'/sessions/'+s['id'],x,'PUT').status_code,409)
        x['device_id']='device1';x['exercises'][0]['name']='Tampered'
        self.assertEqual(self.send(self.client,'/sessions/'+s['id'],x,'PUT').status_code,403)
    def test_plan_only_one_session(self):
        s=self.prepared()
        x={'operation_id':uid(),'device_id':'device1','profile_id':self.profile['id'],'plan_id':s['plan_id'],'name':'Plan'}
        self.assertEqual(self.send(self.client,'/sessions/prepare',x).json['data']['id'],s['id'])
        x['operation_id']=uid();x['device_id']='device2'
        self.assertEqual(self.send(self.client,'/sessions/prepare',x).status_code,409)
    def test_body_weight_validation_and_correction(self):
        path='/clients/'+self.profile['id']+'/body-weights'
        for value in ('NaN','Infinity','-1','0'):
            self.assertEqual(self.send(self.trainer,path,{'operation_id':uid(),'measurement_date':today(),'weight_lb':value}).status_code,400)
        x={'operation_id':uid(),'measurement_date':today(),'weight_lb':'155.25'}
        self.assertEqual(self.send(self.client,path,x).status_code,403)
        w=self.send(self.trainer,path,x).json['data']
        self.assertEqual(self.send(self.trainer,'/body-weights/'+w['id'],{'operation_id':uid(),'weight_lb':'154.5'},'PATCH').json['data']['weight_lb'],'154.5')
    def test_invalid_completed_and_future_date(self):
        s=self.prepared();x=self.upload(s);x['exercises'][0]['sets']=[]
        self.assertEqual(self.send(self.client,'/sessions/'+s['id'],x,'PUT').status_code,400)
        x=self.upload(s);x['workout_date']='2999-01-01'
        self.assertEqual(self.send(self.client,'/sessions/'+s['id'],x,'PUT').status_code,400)
    def test_persistent_restart(self):
        s=self.prepared();self.send(self.client,'/sessions/'+s['id'],self.upload(s),'PUT')
        restarted=create_app({'TESTING':True,'DATABASE':self.app.config['DATABASE']}).test_client()
        self.send(restarted,'/login',{'email':'trainer@test.com','password':'testpass123'})
        self.assertEqual(len(restarted.get('/api/clients/'+self.profile['id']+'/history').json['data']),1)
    def test_single_trainer_connection(self):
        p=self.send(self.other,'/clients',{'name':'Other'}).json['data']
        self.assertEqual(self.send(self.other,'/invitations',{'profile_id':p['id'],'client_email':'client@test.com'}).status_code,409)

if __name__=='__main__': unittest.main()
