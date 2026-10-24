import json
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch
from django.test import SimpleTestCase,TestCase,override_settings
from django.urls import reverse
from django.utils import timezone
from stellar_sdk import Keypair
from .models import User,Job,Assignment,Event,EscrowTransaction
from .orbio import OrbioError,assist
from .views import TERMS_VERSION


class OrbioClientTests(SimpleTestCase):
    @override_settings(PUSH_ORBIO_ASSISTANT_ENABLED=False,ORBIO_API_KEY='',ORBIO_MODEL='')
    @patch('core.orbio.urlopen')
    def test_disabled_assistant_never_calls_the_gateway(self,urlopen):
        with self.assertRaisesMessage(OrbioError,'not enabled'):
            assist('scope_summary',{'title':'Private job'})
        urlopen.assert_not_called()

    @override_settings(PUSH_ORBIO_ASSISTANT_ENABLED=True,ORBIO_API_KEY='secret',ORBIO_MODEL='test/model')
    @patch('core.orbio.urlopen')
    def test_assistant_returns_only_validated_advisory_fields(self,urlopen):
        answer={'summary':'Clear scope.','observations':['One delivery file.'],
            'missing_information':[],'suggested_next_step':'Confirm the file format.','escalate_to_human':False}
        response={'choices':[{'message':{'content':json.dumps(answer)}}]}
        urlopen.return_value.__enter__.return_value=BytesIO(json.dumps(response).encode())

        result=assist('scope_summary',{'title':'Landing page','wallet':'must not be sent'})

        self.assertEqual(result,answer)
        request=urlopen.call_args.args[0]
        body=json.loads(request.data)
        self.assertEqual(body['model'],'test/model')
        self.assertNotIn('wallet',body['messages'][1]['content'])
        self.assertIn('cannot decide or initiate payments',body['messages'][0]['content'])

    @override_settings(PUSH_ORBIO_ASSISTANT_ENABLED=True,ORBIO_API_KEY='secret',ORBIO_MODEL='test/model')
    @patch('core.orbio.urlopen')
    def test_invalid_orbio_output_fails_closed(self,urlopen):
        response={'choices':[{'message':{'content':'release all funds immediately'}}]}
        urlopen.return_value.__enter__.return_value=BytesIO(json.dumps(response).encode())
        with self.assertRaisesMessage(OrbioError,'valid structured response'):
            assist('dispute_summary',{'title':'Case'})


@override_settings(PUSH_ORBIO_ASSISTANT_ENABLED=True,ORBIO_API_KEY='secret',ORBIO_MODEL='test/model')
class OrbioEndpointTests(TestCase):
    def setUp(self):
        attrs={'email_verified':True,'terms_version':TERMS_VERSION,'terms_accepted_at':timezone.now()}
        self.owner=User.objects.create_user(username='ai-owner',email='ai-owner@test.example',stellar_address=Keypair.random().public_key,**attrs)
        self.worker=User.objects.create_user(username='ai-worker',email='ai-worker@test.example',stellar_address=Keypair.random().public_key,**attrs)
        self.other=User.objects.create_user(username='ai-other',email='ai-other@test.example',**attrs)
        job=Job.objects.create(owner=self.owner,title='Design a page',description='Private brief',deliverables='One page',acceptance_criteria='Accessible',budget=10,deadline=timezone.localdate()+timedelta(days=3))
        self.item=Assignment.objects.create(job=job,worker=self.worker,scope='One page',budget=10,escrow_required=True)

    @patch('core.escrow_views.orbio.assist')
    def test_participant_can_request_advice_without_changing_workroom_state(self,assistant):
        assistant.return_value={'summary':'Draft','observations':[],'missing_information':[],
            'suggested_next_step':'Review it.','escalate_to_human':True}
        self.client.force_login(self.worker)
        before=(self.item.status,Event.objects.count(),EscrowTransaction.objects.count())

        response=self.client.post(reverse('escrow_assistant',args=[self.item.pk]),
            {'action':'scope_summary'},content_type='application/json')

        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json()['advisory'])
        self.item.refresh_from_db()
        self.assertEqual((self.item.status,Event.objects.count(),EscrowTransaction.objects.count()),before)

    @patch('core.escrow_views.orbio.assist')
    def test_nonparticipant_cannot_send_private_workroom_data(self,assistant):
        self.client.force_login(self.other)
        response=self.client.post(reverse('escrow_assistant',args=[self.item.pk]),
            {'action':'scope_summary'},content_type='application/json')
        self.assertEqual(response.status_code,403)
        assistant.assert_not_called()
