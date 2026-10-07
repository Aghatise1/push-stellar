from types import SimpleNamespace as Obj
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from stellar_sdk import Keypair, Account, TransactionBuilder, Network
from .escrow import require_enabled, token_address, validate_signature
from .escrow_policy import action_payload
from .stellar import StellarVerificationError

class EscrowPolicyTests(SimpleTestCase):
    def setUp(self):
        self.item=Obj(job=Obj(owner_id=1),worker_id=2,status='awaiting_funding')
        self.agreement=Obj(reviewer_id=3,chain_status='Unfunded',accepted_at=True,amount=100)
    @patch('core.escrow_policy.has_staff_access',return_value=True)
    def test_roles_and_states(self,staff):
        valid={'fund':('Unfunded',1),'submit':('Funded',2),'approve':('Submitted',1),'revise':('Submitted',1),'refund_expired':('Funded',1),'claim_expired':('Submitted',2),'resolve':('Disputed',3)}
        for action,(state,actor) in valid.items():
            self.agreement.chain_status=state
            data={'notes':'Delivered','note':'Evidence reviewed','worker_amount':'60'}
            action_payload(self.item,self.agreement,Obj(pk=actor),action,data)
            for intruder in (4,5):
                with self.assertRaises(StellarVerificationError):action_payload(self.item,self.agreement,Obj(pk=intruder),action,data)
        self.agreement.chain_status='Released'
        for action in valid:
            with self.assertRaises(StellarVerificationError):action_payload(self.item,self.agreement,Obj(pk=1),action,{})
    @patch('core.escrow_policy.has_staff_access',return_value=False)
    def test_revoked_reviewer_and_invalid_splits(self,staff):
        self.agreement.chain_status='Disputed'
        with self.assertRaises(StellarVerificationError):action_payload(self.item,self.agreement,Obj(pk=3),'resolve',{'note':'Reason','worker_amount':'50'})
        staff.return_value=True
        for value in ('-1','101','1.5','garbage'):
            with self.assertRaises(StellarVerificationError):action_payload(self.item,self.agreement,Obj(pk=3),'resolve',{'note':'Reason','worker_amount':value})
        split=action_payload(self.item,self.agreement,Obj(pk=3),'resolve',{'note':'Reason','worker_amount':'60'})
        self.assertEqual(split['worker_amount']+split['client_amount'],100)
    @override_settings(PUSH_TESTNET_ESCROW_ENABLED=False)
    def test_disabled_by_default(self):
        with self.assertRaises(StellarVerificationError):require_enabled()
    @override_settings(PUSH_TESTNET_ESCROW_ENABLED=True,PUSH_TESTNET_ESCROW_CONTRACT='Ctest',STELLAR_TESTNET_SOROBAN_RPC='https://mainnet.example',STELLAR_TESTNET_USDC_ISSUER='wrong')
    def test_non_testnet_configuration_rejected(self):
        with self.assertRaises(StellarVerificationError):require_enabled()
    def test_signature_must_match_exact_transaction_and_wallet(self):
        signer=Keypair.random();other=Keypair.random()
        tx=TransactionBuilder(Account(signer.public_key,1),Network.TESTNET_NETWORK_PASSPHRASE,100).append_manage_data_op('test','value').set_timeout(300).build()
        record=Obj(source=signer.public_key,tx_hash=tx.hash_hex())
        tx.sign(other)
        with self.assertRaises(StellarVerificationError):validate_signature(record,tx.to_xdr())
        tx.sign(signer);validate_signature(record,tx.to_xdr())
        record.tx_hash='0'*64
        with self.assertRaises(StellarVerificationError):validate_signature(record,tx.to_xdr())
    def test_assets_are_distinct_testnet_contracts(self):
        self.assertNotEqual(token_address('USDC'),token_address('XLM'))
        with self.assertRaises(StellarVerificationError):token_address('BTC')

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from .models import User,Job,Assignment,EscrowAgreement,EscrowTransaction,Payment
from .escrow_records import reconcile

class EscrowRecordTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user(username='escrow-owner',email='owner@escrow.test')
        self.worker=User.objects.create_user(username='escrow-worker',email='worker@escrow.test')
        self.reviewer=User.objects.create_user(username='escrow-reviewer',email='reviewer@escrow.test')
        self.job=Job.objects.create(owner=self.owner,project='Test',title='Test escrow',description='Test',deliverables='Test',category='UI/UX Design',budget=100,deadline=timezone.localdate()+timedelta(days=7))
        self.item=Assignment.objects.create(job=self.job,worker=self.worker,scope='Test',budget=100,status='awaiting_funding',escrow_required=True)
        self.agreement=EscrowAgreement.objects.create(assignment=self.item,reviewer=self.reviewer,contract='Ctest',agreement_id='0'*64,client_address='client',worker_address='worker',reviewer_address='reviewer',asset='XLM',token_address='token',amount=100,deadline=9999999999,review_seconds=86400,revision_limit=2,accepted_at=timezone.now())
        self.record=EscrowTransaction.objects.create(escrow=self.agreement,actor=self.owner,action='fund',source='client',prepared_xdr='test',tx_hash='1'*64,state='pending')
    @patch('core.escrow_records.chain.server')
    @patch('core.escrow_records.chain.read_agreement')
    def test_no_optimistic_funding_then_idempotent_confirmation(self,read,server):
        from stellar_sdk.soroban_rpc import GetTransactionStatus as Status
        server.return_value.get_transaction.return_value=Obj(status=Status.NOT_FOUND)
        self.assertFalse(reconcile(self.record))
        self.item.refresh_from_db();self.assertEqual(self.item.status,'awaiting_funding')
        read.return_value={'status':['Funded'],'deadline':9999999999,'review_until':0}
        server.return_value.get_transaction.return_value=Obj(status=Status.SUCCESS)
        self.assertTrue(reconcile(self.record));self.assertTrue(reconcile(self.record))
        self.item.refresh_from_db();self.assertEqual(self.item.status,'funded')
        self.assertEqual(self.item.events.count(),1);self.assertEqual(Payment.objects.count(),0)
    @patch('core.escrow_records.chain.server')
    def test_failed_transaction_does_not_unlock_work(self,server):
        from stellar_sdk.soroban_rpc import GetTransactionStatus as Status
        server.return_value.get_transaction.return_value=Obj(status=Status.FAILED)
        with self.assertRaises(StellarVerificationError):reconcile(self.record)
        self.item.refresh_from_db();self.record.refresh_from_db()
        self.assertEqual(self.item.status,'awaiting_funding');self.assertEqual(self.record.state,'failed')
    @patch('core.escrow_records.chain.server')
    @patch('core.escrow_records.chain.read_agreement')
    def test_release_creates_one_real_testnet_record(self,read,server):
        from stellar_sdk.soroban_rpc import GetTransactionStatus as Status
        self.record.action='approve';self.record.save()
        read.return_value={'status':['Released'],'deadline':9999999999,'review_until':9999999999}
        server.return_value.get_transaction.return_value=Obj(status=Status.SUCCESS)
        reconcile(self.record);reconcile(self.record)
        self.assertEqual(Payment.objects.count(),1)
        self.assertFalse(Payment.objects.get().simulated)
        self.agreement.refresh_from_db();self.assertEqual(self.agreement.worker_paid,100)

    @patch('core.escrow_records.chain.server')
    def test_expiry_requires_full_rpc_history_coverage(self,server):
        from stellar_sdk.soroban_rpc import GetTransactionStatus as Status
        signer=Keypair.random()
        tx=TransactionBuilder(Account(signer.public_key,1),Network.TESTNET_NETWORK_PASSPHRASE,100).append_manage_data_op('test','value').set_timeout(300).build()
        self.record.prepared_xdr=tx.to_xdr();self.record.save()
        end=tx.transaction.preconditions.time_bounds.max_time
        created=int(self.record.created_at.timestamp())
        server.return_value.get_transaction.return_value=Obj(status=Status.NOT_FOUND,oldest_ledger_close_time=created+10,latest_ledger_close_time=end+10)
        self.assertFalse(reconcile(self.record))
        self.record.refresh_from_db();self.assertEqual(self.record.state,'pending')
        server.return_value.get_transaction.return_value=Obj(status=Status.NOT_FOUND,oldest_ledger_close_time=created-10,latest_ledger_close_time=end+10)
        with self.assertRaisesMessage(StellarVerificationError,'expired without ledger inclusion'):reconcile(self.record)
        self.record.refresh_from_db();self.item.refresh_from_db()
        self.assertEqual(self.record.state,'expired');self.assertEqual(self.item.status,'awaiting_funding')

from django.urls import reverse
from .models import StaffAccess,Dispute
from .views import TERMS_VERSION

@override_settings(PUSH_TESTNET_ESCROW_ENABLED=False,PUSH_TESTNET_ESCROW_CONTRACT='')
class EscrowEndpointTests(TestCase):
    def setUp(self):
        self.owner=self.person('owner');self.worker=self.person('worker');self.reviewer=self.person('reviewer');self.other=self.person('other')
        self.job=Job.objects.create(owner=self.owner,title='Escrow test',budget=100,deadline=timezone.localdate()+timedelta(days=7))
        self.item=Assignment.objects.create(job=self.job,worker=self.worker,budget=100,scope='Delivery',escrow_required=True)
    def person(self,name):
        return User.objects.create_user(username=name,email=name+'@test.example',email_verified=True,terms_version=TERMS_VERSION,terms_accepted_at=timezone.now(),stellar_address=Keypair.random().public_key)
    def agreement(self):
        return EscrowAgreement.objects.create(assignment=self.item,reviewer=self.reviewer,contract='Ctest',agreement_id='a'*64,client_address=self.owner.stellar_address,worker_address=self.worker.stellar_address,reviewer_address=self.reviewer.stellar_address,asset='XLM',token_address='token',amount=100,deadline=9999999999,review_seconds=86400,revision_limit=2)
    def test_disabled_screen_and_all_mutations_fail_closed(self):
        self.agreement();self.client.force_login(self.worker)
        self.assertContains(self.client.get(reverse('assignment',args=[self.item.pk])),'Escrow testing is disabled')
        for action in ('accept','configure','fund','approve','cancel'):
            response=self.client.post(reverse('assignment_action',args=[self.item.pk]),{'action':action,'accept_terms':'on','accept_xlm':'on'})
            self.assertEqual(response.status_code,400)
        for endpoint in ('escrow_prepare','escrow_submit'):
            self.assertEqual(self.client.post(reverse(endpoint,args=[self.item.pk]),{},content_type='application/json').status_code,400)
        self.item.refresh_from_db();self.assertEqual(self.item.status,'awaiting_acceptance')
        self.assertEqual(EscrowTransaction.objects.count(),0)
    def test_private_evidence_and_named_reviewer_access(self):
        self.agreement();self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('escrow_detail',args=[self.item.pk])).status_code,403)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(reverse('escrow_detail',args=[self.item.pk])).status_code,403)
        StaffAccess.objects.create(user=self.reviewer,role='trust_support',status='approved')
        self.assertEqual(self.client.get(reverse('escrow_detail',args=[self.item.pk])).status_code,200)
    @override_settings(PUSH_TESTNET_ESCROW_ENABLED=True,PUSH_TESTNET_ESCROW_CONTRACT='Ctest')
    def test_worker_must_acknowledge_xlm_and_correct_wallet(self):
        agreement=self.agreement();StaffAccess.objects.create(user=self.reviewer,role='trust_support',status='approved');self.client.force_login(self.worker)
        url=reverse('assignment_action',args=[self.item.pk])
        self.assertEqual(self.client.post(url,{'action':'accept','accept_terms':'on','accept_xlm':'on'}).status_code,400)
        session=self.client.session;session['wallet_connected_address']=self.worker.stellar_address;session.save()
        self.assertEqual(self.client.post(url,{'action':'accept','accept_terms':'on'}).status_code,400)
        self.assertEqual(self.client.post(url,{'action':'accept','accept_terms':'on','accept_xlm':'on'}).status_code,302)
        self.item.refresh_from_db();agreement.refresh_from_db()
        self.assertEqual(self.item.status,'awaiting_funding');self.assertTrue(agreement.xlm_acknowledged)
        self.assertEqual(Payment.objects.count(),0)
    def test_legacy_staff_resolution_cannot_simulate_escrow_payout(self):
        self.agreement();self.item.status='disputed';self.item.save()
        dispute=Dispute.objects.create(assignment=self.item,opened_by=self.worker,reason='Review needed')
        StaffAccess.objects.create(user=self.reviewer,role='trust_support',status='approved')
        self.client.force_login(self.reviewer)
        response=self.client.post(reverse('moderate_dispute',args=[dispute.pk]),{'resolution':'release','decision_note':'Reviewed'})
        self.assertRedirects(response,reverse('escrow_detail',args=[self.item.pk]))
        self.item.refresh_from_db();self.assertEqual(self.item.status,'disputed');self.assertEqual(Payment.objects.count(),0)
    def test_old_assignment_keeps_original_workroom(self):
        self.item.escrow_required=False;self.item.save();self.client.force_login(self.owner)
        response=self.client.get(reverse('assignment',args=[self.item.pk]))
        self.assertTemplateUsed(response,'legacy_assignment.html');self.assertNotContains(response,'data-escrow-room')

    @override_settings(PUSH_TESTNET_ESCROW_ENABLED=True,PUSH_TESTNET_ESCROW_CONTRACT='Ctest')
    def test_xlm_totals_are_separate_from_dollar_totals(self):
        self.item.agreement_snapshot={'payment_asset':'XLM'};self.item.status='paid';self.item.save()
        Payment.objects.create(assignment=self.item,amount=100,method='escrow_xlm',simulated=False)
        self.client.force_login(self.worker)
        response=self.client.get(reverse('payments'))
        self.assertEqual(response.context['verified_earnings'],0)
        self.assertEqual(response.context['xlm_earnings'],100)
        self.assertContains(response,'100 test XLM')
    def test_testnet_asset_selector_accepts_xlm_even_before_activation(self):
        from .forms import JobForm
        form=JobForm({'project':'Test','title':'Test job','category':'UI/UX Design','description':'Brief','deliverables':'File','budget':100,'payment_asset':'XLM','deadline':str(self.job.deadline)})
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data['payment_asset'],'XLM')

    @override_settings(PUSH_TESTNET_ESCROW_ENABLED=True,PUSH_TESTNET_ESCROW_CONTRACT='Ctest')
    @patch('core.escrow_records.chain.read_agreement')
    @patch('core.escrow.server')
    @patch('core.escrow.build')
    def test_signed_endpoint_waits_for_confirmation_and_retries_idempotently(self,build,server,read):
        from stellar_sdk.soroban_rpc import GetTransactionStatus as Get,SendTransactionStatus as Send
        signer=Keypair.random();self.owner.stellar_address=signer.public_key;self.owner.save()
        agreement=self.agreement();agreement.accepted_at=timezone.now();agreement.save()
        self.item.status='awaiting_funding';self.item.save()
        self.client.force_login(self.owner)
        session=self.client.session;session['wallet_connected_address']=signer.public_key;session.save()
        tx=TransactionBuilder(Account(signer.public_key,1),Network.TESTNET_NETWORK_PASSPHRASE,100).append_manage_data_op('test','value').set_timeout(300).build()
        build.return_value=tx
        url=reverse('escrow_prepare',args=[self.item.pk])
        response=self.client.post(url,{'action':'fund'},content_type='application/json')
        self.assertEqual(response.status_code,200);token=response.json()['token']
        self.assertEqual(self.client.post(url,{'action':'fund'},content_type='application/json').status_code,400)
        tx.sign(signer)
        server.return_value.get_transaction.return_value=Obj(status=Get.NOT_FOUND)
        server.return_value.send_transaction.return_value=Obj(status=Send.PENDING)
        submit=reverse('escrow_submit',args=[self.item.pk])
        response=self.client.post(submit,{'token':token,'signedXdr':tx.to_xdr()},content_type='application/json')
        self.assertTrue(response.json()['pending']);self.item.refresh_from_db();self.assertEqual(self.item.status,'awaiting_funding')
        server.return_value.get_transaction.return_value=Obj(status=Get.SUCCESS)
        read.return_value={'status':['Funded'],'deadline':9999999999,'review_until':0}
        self.assertIn('redirectUrl',self.client.post(submit,{'token':token},content_type='application/json').json())
        self.assertIn('redirectUrl',self.client.post(submit,{'token':token},content_type='application/json').json())
        self.item.refresh_from_db();self.assertEqual(self.item.status,'funded')
        self.assertEqual(server.return_value.send_transaction.call_count,1)
        self.assertEqual(self.item.events.count(),1)


@override_settings(PUSH_TESTNET_ONLY=True,PUSH_TESTNET_ESCROW_ENABLED=True,PUSH_TESTNET_ESCROW_STAFF_CONTRACT='Ctest')
class WalletSetupRecoveryTests(TestCase):
    setUp=EscrowEndpointTests.setUp
    person=EscrowEndpointTests.person

    def connect(self,user):
        self.client.force_login(user)
        response=self.client.post(reverse('wallet_connect'),{'address':user.stellar_address,'network':'TESTNET'},content_type='application/json')
        self.assertEqual(response.status_code,200)

    def configure(self):
        return self.client.post(reverse('assignment_action',args=[self.item.pk]),{'action':'configure'})

    def assert_inline(self,response,text):
        self.assertEqual(response.status_code,400)
        self.assertTemplateUsed(response,'escrow_assignment.html')
        self.assertContains(response,text,status_code=400)
        self.assertContains(response,'Connect my testnet wallet',status_code=400)
        self.assertEqual(EscrowAgreement.objects.count(),0)
        self.assertEqual(EscrowTransaction.objects.count(),0)

    def test_disconnected_client_gets_inline_recovery(self):
        self.client.force_login(self.owner)
        self.assert_inline(self.configure(),'Your wallet is disconnected')

    def test_missing_worker_wallet_names_the_person_who_must_connect(self):
        self.worker.stellar_address='';self.worker.save()
        self.connect(self.owner)
        self.assert_inline(self.configure(),'The worker has not saved a valid wallet')

    def test_shared_wallet_remains_blocked(self):
        self.worker.stellar_address=self.owner.stellar_address;self.worker.save()
        self.connect(self.owner)
        self.assert_inline(self.configure(),'using the same wallet')

    @patch('core.escrow_views.chain.token_address',return_value='token')
    @patch('core.escrow_views.chain.registry_owner')
    def test_separate_wallet_connections_recover_configuration_and_acceptance(self,registry,token):
        from .models import EscrowStaffWallet
        StaffAccess.objects.create(user=self.reviewer,role='owner',status='approved')
        EscrowStaffWallet.objects.create(user=self.reviewer,address=self.reviewer.stellar_address)
        registry.return_value=self.reviewer.stellar_address
        self.connect(self.worker)
        self.connect(self.owner)
        self.assertEqual(self.configure().status_code,302)
        agreement=EscrowAgreement.objects.get(assignment=self.item)
        self.assertEqual(agreement.client_address,self.owner.stellar_address)
        self.assertEqual(agreement.worker_address,self.worker.stellar_address)
        self.connect(self.worker)
        result=self.client.post(reverse('assignment_action',args=[self.item.pk]),{'action':'accept','accept_terms':'on','accept_xlm':'on'})
        self.assertEqual(result.status_code,302)
        self.item.refresh_from_db();self.assertEqual(self.item.status,'awaiting_funding')
        self.assertEqual(EscrowTransaction.objects.count(),0)
